/* SsamSsam by SeoulCook Artisan — site behaviour
   - bilingual KO/EN toggle (?lang= param, no storage APIs)
   - mobile navigation
   - scroll reveal
   - inquiry form: posts to FORM_ENDPOINT if configured, otherwise opens mail client
*/
(function () {
  'use strict';

  /* ---- CONFIG : replace with your Formspree / Basin endpoint when ready ---- */
  var FORM_ENDPOINT = '';                       // e.g. 'https://formspree.io/f/xxxxxxx'
  var FALLBACK_MAIL = 'export@seoulcook.com';   // used when FORM_ENDPOINT is empty
  /* ------------------------------------------------------------------------ */

  var LANG = 'ko';
  var html = document.documentElement;

  var STR = {
    ko: {
      sent: '문의가 접수되었습니다. 영업일 기준 72시간 내 회신드립니다.',
      mail: '메일 앱이 열립니다. 내용 확인 후 전송해 주세요.',
      err: '전송에 실패했습니다. export@seoulcook.com 으로 보내주세요.',
      soon: '2026년 11월 자사몰 오픈 예정입니다. 뉴스레터로 알려드릴게요.',
      copy: '주소가 복사되었습니다.',
      ph: '관심 품목, 예상 물량(MOQ), 희망 납기, 유통 채널을 적어주세요.'
    },
    en: {
      sent: 'Thank you — our team replies within 72 business hours.',
      mail: 'Your mail app will open. Please review and send.',
      err: 'Could not send. Please email export@seoulcook.com directly.',
      soon: 'Our online store opens November 2026. Join the list and we will tell you first.',
      copy: 'Copied to clipboard.',
      ph: 'Products of interest, target volume (MOQ), required lead time, retail channel.'
    }
  };
  function t(k) { return STR[LANG][k]; }

  /* ---------------- language ---------------- */
  function setLang(l, push) {
    LANG = (l === 'en') ? 'en' : 'ko';
    html.lang = LANG;

    var ko = document.getElementById('lang-ko');
    var en = document.getElementById('lang-en');
    if (ko) ko.setAttribute('aria-pressed', String(LANG === 'ko'));
    if (en) en.setAttribute('aria-pressed', String(LANG === 'en'));

    document.querySelectorAll('[data-t-ko]').forEach(function (el) {
      var v = el.getAttribute(LANG === 'en' ? 'data-t-en' : 'data-t-ko');
      if (v === null) return;
      if (el.tagName === 'OPTION') el.textContent = v;
      else if ('placeholder' in el) el.placeholder = v;
      else el.textContent = v;
    });

    var ttl = document.body.getAttribute(LANG === 'en' ? 'data-title-en' : 'data-title-ko');
    if (ttl) document.title = ttl;
    var dsc = document.body.getAttribute(LANG === 'en' ? 'data-desc-en' : 'data-desc-ko');
    var m = document.querySelector('meta[name="description"]');
    if (dsc && m) m.setAttribute('content', dsc);

    document.querySelectorAll('a[href]').forEach(function (a) {
      var h = a.getAttribute('href');
      if (!h || /^(https?:|mailto:|tel:|#)/.test(h)) return;
      var hash = '', qi;
      var i = h.indexOf('#');
      if (i > -1) { hash = h.slice(i); h = h.slice(0, i); }
      qi = h.indexOf('?');
      if (qi > -1) h = h.slice(0, qi);
      a.setAttribute('href', h + (LANG === 'en' ? '?lang=en' : '') + hash);
    });

    if (push && window.history && history.replaceState) {
      var u = location.pathname + (LANG === 'en' ? '?lang=en' : '') + location.hash;
      history.replaceState(null, '', u);
    }
  }
  window.setLang = setLang;

  var qs = new URLSearchParams(location.search).get('lang');
  if (qs === 'en' || qs === 'ko') setLang(qs, false);
  else setLang((navigator.language || 'ko').slice(0, 2) === 'ko' ? 'ko' : 'en', false);

  /* ---------------- mobile nav ---------------- */
  var burger = document.getElementById('burger');
  var nav = document.getElementById('nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      burger.setAttribute('aria-expanded', String(open));
    });
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------------- toast ---------------- */
  var tEl = document.getElementById('toast'), tTimer;
  function toast(msg) {
    if (!tEl) return;
    tEl.textContent = msg;
    tEl.classList.add('on');
    clearTimeout(tTimer);
    tTimer = setTimeout(function () { tEl.classList.remove('on'); }, 3400);
  }
  window.toast = toast;
  window.notifySoon = function (e) { if (e) e.preventDefault(); toast(t('soon')); };

  /* ---------------- scroll reveal ---------------- */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    document.querySelectorAll('.rv').forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll('.rv').forEach(function (el) { el.classList.add('in'); });
  }

  /* ---------------- forms ---------------- */
  document.querySelectorAll('form[data-inquiry]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      var btn = form.querySelector('button[type="submit"]');

      if (FORM_ENDPOINT) {
        if (btn) btn.disabled = true;
        fetch(FORM_ENDPOINT, { method: 'POST', body: fd, headers: { Accept: 'application/json' } })
          .then(function (r) {
            if (!r.ok) throw new Error('bad status');
            form.reset(); setLang(LANG, false); toast(t('sent'));
          })
          .catch(function () { toast(t('err')); })
          .then(function () { if (btn) btn.disabled = false; });
        return;
      }

      var lines = [];
      fd.forEach(function (v, k) { if (String(v).trim()) lines.push(k + ': ' + v); });
      var subject = '[Website Inquiry] ' + (fd.get('company') || fd.get('name') || 'SsamSsam');
      location.href = 'mailto:' + FALLBACK_MAIL +
        '?subject=' + encodeURIComponent(subject) +
        '&body=' + encodeURIComponent(lines.join('\n'));
      toast(t('mail'));
    });
  });

  /* ---------------- footer year ---------------- */
  var y = document.getElementById('yr');
  if (y) y.textContent = new Date().getFullYear();
})();
