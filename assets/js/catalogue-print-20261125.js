/* Print the catalogue's vector pages only after all pages and images are ready. */
(function () {
  'use strict';
  var params = new URLSearchParams(location.search);
  var language = params.get('lang') || 'ko';
  var languages = ['ko','en','es','zh','ja','ar','fr','de','it'];
  if (languages.indexOf(language) === -1) language = 'ko';
  var ui = language === 'ko' ? 'ko' : 'en';document.documentElement.lang = ui;
  var id = params.get('document') || 'complete';
  if (['complete','company','products'].indexOf(id) === -1) id = 'complete';
  var pages = document.getElementById('print-pages');
  var button = document.getElementById('print-document');
  var retry = document.getElementById('print-retry');
  var status = document.getElementById('print-status');
  var title = document.getElementById('print-title');
  var back = document.getElementById('catalogue-back');back.href = '/catalogues/' + (ui === 'en' ? '?lang=en' : '');
  var text = ui === 'ko' ? {
    loading:'문서를 준비하고 있습니다.',ready:'A4 · 인쇄 배율 100% 또는 실제 크기를 선택해 주세요.',failed:'문서를 불러오지 못했습니다. 다시 시도해 주세요.',printing:'인쇄 창이 열립니다. 열리지 않으면 인쇄하기 버튼을 선택해 주세요.'
  } : {
    loading:'Preparing your document.',ready:'A4 · Select 100% scale or Actual size when printing.',failed:'We could not load the document. Please try again.',printing:'The print window will open. If it does not, select Print.'
  };
  var svgNS = 'http://www.w3.org/2000/svg';
  var permitted = ['svg','g','defs','path','rect','circle','ellipse','polygon','polyline','line','text','tspan','image','use','clipPath','mask','linearGradient','radialGradient','stop','pattern','symbol','filter','feColorMatrix','title','desc'];
  var automaticDone = false;
  function localAsset(path,suffix) {
    if (typeof path !== 'string' || !/^\/assets\/catalogues\/[A-Za-z0-9_./-]+$/.test(path) || path.indexOf('..') !== -1 || !path.endsWith(suffix)) throw new Error('Invalid print asset');
    return path;
  }
  function sanitise(source,index) {
    if (source.length > 12000000) throw new Error('Print page too large');
    var xml = new DOMParser().parseFromString(source,'image/svg+xml');
    if (xml.querySelector('parsererror') || xml.documentElement.localName !== 'svg') throw new Error('Invalid print page');
    var svg = xml.documentElement;
    [svg].concat(Array.prototype.slice.call(svg.querySelectorAll('*'))).forEach(function (node) {
      if (node.namespaceURI !== svgNS || permitted.indexOf(node.localName) === -1) {node.remove();return;}
      Array.prototype.slice.call(node.attributes).forEach(function (attr) {
        var name = attr.localName.toLowerCase();var value = attr.value;
        if (name.indexOf('on') === 0 || name === 'style' || name === 'base') {node.removeAttributeNode(attr);return;}
        if (name === 'href') {
          if (value.charAt(0) === '#') return;
          if (node.localName !== 'image' || !/^\/assets\/catalogues\/[A-Za-z0-9_./-]+\.(png|jpe?g)$/i.test(value) || value.indexOf('..') !== -1) node.removeAttributeNode(attr);
        }
        if (/url\(/i.test(value) && !/^url\(#[A-Za-z0-9_.:-]+\)$/.test(value)) node.removeAttributeNode(attr);
      });
    });
    var prefix = 'catalogue-page-' + index + '-';
    [svg].concat(Array.prototype.slice.call(svg.querySelectorAll('*'))).forEach(function (node) {
      Array.prototype.slice.call(node.attributes).forEach(function (attr) {
        if (attr.localName === 'id') attr.value = prefix + attr.value;
        else if (attr.localName === 'href' && attr.value.charAt(0) === '#') attr.value = '#' + prefix + attr.value.slice(1);
        else if (/^url\(#/.test(attr.value)) attr.value = attr.value.replace('url(#','url(#' + prefix);
      });
    });
    svg.removeAttribute('width');svg.removeAttribute('height');
    svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
    return document.importNode(svg,true);
  }
  function waitForImages() {
    return Promise.all(Array.prototype.map.call(pages.querySelectorAll('image'),function (node) {
      var href = node.getAttribute('href') || node.getAttributeNS('http://www.w3.org/1999/xlink','href');
      if (!href) throw new Error('Missing print image');
      return new Promise(function (resolve,reject) {
        var image = new Image();image.onload = function () {if (!image.naturalWidth) reject(new Error('Empty print image'));else resolve();};image.onerror = reject;image.src = href;
      });
    }));
  }
  function print() {if (document.body.dataset.printReady !== 'true') return;status.textContent = text.printing;window.print();}
  async function load() {
    document.body.removeAttribute('data-print-ready');button.disabled = true;retry.hidden = true;pages.setAttribute('aria-busy','true');pages.replaceChildren();status.textContent = text.loading;
    try {
      var response = await fetch('/assets/catalogues/manifest-20261125.json',{cache:'no-cache'});if (!response.ok) throw new Error('Catalogue unavailable');
      var manifest = await response.json();if (!manifest || !Array.isArray(manifest.documents)) throw new Error('Invalid catalogue list');
      var doc = manifest.documents.find(function (item) {return item.id === id && item.language === language;});
      if (!doc || !Array.isArray(doc.print_pages) || !doc.print_pages.length || doc.print_pages.length > 100) throw new Error('Print pages unavailable');
      if (doc.print_pages.length !== Number(doc.pages)) throw new Error('Incomplete print pages');
      title.textContent = doc.title;document.title = doc.title + (ui === 'ko' ? ' · 인쇄' : ' · Print');
      var rendered = await Promise.all(doc.print_pages.map(async function (path,index) {
        var pageResponse = await fetch(localAsset(path,'.svg'),{cache:'force-cache'});if (!pageResponse.ok) throw new Error('Print page unavailable');
        var section = document.createElement('section');section.className = 'print-page';section.setAttribute('aria-label',(ui === 'ko' ? '쪽 ' : 'Page ') + (index + 1));section.append(sanitise(await pageResponse.text(),index));return section;
      }));
      rendered.forEach(function (section) {pages.append(section);});await waitForImages();
      document.body.dataset.printReady = 'true';pages.setAttribute('aria-busy','false');button.disabled = false;status.textContent = text.ready;
      if (params.get('auto') === '1' && !automaticDone) {automaticDone = true;await new Promise(function (resolve) {requestAnimationFrame(function () {requestAnimationFrame(resolve);});});print();}
    } catch (e) {
      pages.replaceChildren();pages.setAttribute('aria-busy','false');status.textContent = text.failed;retry.hidden = false;
    }
  }
  button.addEventListener('click',print);retry.addEventListener('click',load);
  load();
})();
