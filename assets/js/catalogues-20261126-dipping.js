/* Document selection is separate from the website's KO/EN interface. */
(function () {
  'use strict';
  var manifestUrl = '/assets/catalogues/manifest-20261126-dipping.json';
  var languages = {ko:'한국어',en:'English',es:'Español',zh:'简体中文',ja:'日本語',ar:'العربية',fr:'Français',de:'Deutsch',it:'Italiano'};
  var selector = document.getElementById('catalogue-language');
  if (!selector) return;
  var selected = document.documentElement.lang === 'en' ? 'en' : 'ko';
  var chosen = false;
  var manifest = null;
  var error = document.getElementById('catalogue-error');
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-catalogue]'));
  var strings = {
    ko:{loading:'파일 정보 확인 중',unavailable:'파일 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',retry:'다시 시도',pages:'쪽',view:'보기',download:'다운로드',print:'인쇄하기'},
    en:{loading:'Loading file details',unavailable:'We could not load the file details. Please try again.',retry:'Try again',pages:'pages',view:'View',download:'Download',print:'Print'}
  };
  function ui() { return document.documentElement.lang === 'en' ? 'en' : 'ko'; }
  function assetUrl(path) {
    if (typeof path !== 'string' || !/^\/assets\/catalogues\/[A-Za-z0-9_./-]+\.pdf$/.test(path) || path.indexOf('..') !== -1) throw new Error('Invalid catalogue path');
    return new URL(path, location.origin).href;
  }
  function disable(card) {
    card.querySelectorAll('[data-catalogue-view],[data-catalogue-download],[data-catalogue-print]').forEach(function (a) {
      a.removeAttribute('href');a.setAttribute('aria-disabled','true');a.setAttribute('tabindex','-1');
    });
  }
  function showError() {
    error.hidden = false;error.replaceChildren();
    var message = document.createElement('span');message.textContent = strings[ui()].unavailable;
    var retry = document.createElement('button');retry.type = 'button';retry.textContent = strings[ui()].retry;retry.addEventListener('click',load);
    error.append(message,retry);
  }
  function render() {
    var lang = ui();selector.value = selected;
    cards.forEach(function (card) {
      disable(card);
      var meta = card.querySelector('[data-catalogue-meta]');
      if (!manifest) {meta.textContent = strings[lang].loading;return;}
      var doc = manifest.documents.find(function (d) { return d.id === card.getAttribute('data-catalogue') && d.language === selected; });
      if (!doc) {meta.textContent = strings[lang].unavailable;return;}
      try {
        var href = assetUrl(doc.url);
        var pages = Number(doc.pages),bytes = Number(doc.bytes);
        if (!Number.isInteger(pages) || pages < 1 || !Number.isFinite(bytes) || bytes < 1) throw new Error('Invalid file details');
        var size = bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + ' MB' : Math.ceil(bytes / 1024) + ' KB';
        meta.textContent = languages[selected] + ' · ' + pages + (lang === 'ko' ? strings.ko.pages : ' ' + strings.en.pages) + ' · ' + size;
        var view = card.querySelector('[data-catalogue-view]');view.href = href;
        var download = card.querySelector('[data-catalogue-download]');download.href = href;download.download = doc.filename || href.split('/').pop();
        var print = card.querySelector('[data-catalogue-print]');var url = new URL('/catalogues/print/',location.origin);
        url.searchParams.set('document',doc.id);url.searchParams.set('lang',doc.language);url.searchParams.set('auto','1');print.href = url.href;
        [view,download,print].forEach(function (a) { a.removeAttribute('aria-disabled');a.removeAttribute('tabindex'); });
        var title = card.querySelector('h2').innerText;
        view.setAttribute('aria-label',title + ' - ' + languages[selected] + ' - ' + strings[lang].view);
        download.setAttribute('aria-label',title + ' - ' + languages[selected] + ' - ' + strings[lang].download);
        print.setAttribute('aria-label',title + ' - ' + languages[selected] + ' - ' + strings[lang].print);
      } catch (e) {meta.textContent = strings[lang].unavailable;}
    });
    if (!error.hidden) showError();
  }
  function load() {
    error.hidden = true;manifest = null;render();
    fetch(manifestUrl,{cache:'no-cache'}).then(function (response) {
      if (!response.ok) throw new Error('Catalogue list unavailable');return response.json();
    }).then(function (data) {
      if (!data || !Array.isArray(data.documents)) throw new Error('Invalid catalogue list');
      manifest = data;render();
    }).catch(function () { cards.forEach(disable);showError(); });
  }
  selector.addEventListener('change',function () {selected = Object.prototype.hasOwnProperty.call(languages,selector.value) ? selector.value : 'ko';chosen = true;render();});
  new MutationObserver(function () {if (!chosen) selected = ui();render();}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  load();
})();
