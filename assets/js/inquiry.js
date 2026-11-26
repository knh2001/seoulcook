/* Same-origin inquiry delivery. Recipients and credentials exist only in Worker secrets. */
(function () {
  'use strict';
  var copy = {
    ko: {
      loading: '문의 전송 기능을 연결하고 있습니다.',
      ready: '보내기를 누르면 문의가 서울쿡 담당자에게 전송됩니다.',
      unavailable: '현재 자동 전송을 사용할 수 없습니다. export@seoulcook.com으로 직접 메일을 보내주세요.',
      verify: '보안 확인을 완료해 주세요.',
      sending: '문의를 전송하고 있습니다. 창을 닫지 마세요.',
      sent: '문의 전송이 접수되었습니다. 접수번호: ',
      failed: '전송 접수를 확인하지 못했습니다. 입력 내용은 유지됩니다. 중복 전송을 피하려면 export@seoulcook.com으로 접수 여부를 확인해 주세요.',
      limited: '요청이 많습니다. 1분 후 다시 시도해 주세요.'
    },
    en: {
      loading: 'Connecting the inquiry service.',
      ready: 'Select Send to submit your inquiry to the SeoulCook team.',
      unavailable: 'Automatic submission is unavailable. Please email export@seoulcook.com directly.',
      verify: 'Please complete the security check.',
      sending: 'Sending your inquiry. Please keep this page open.',
      sent: 'Your inquiry has been accepted for delivery. Reference: ',
      failed: 'We could not confirm acceptance. Your entries have been kept. To avoid duplicate messages, please check with export@seoulcook.com before resending.',
      limited: 'Too many requests. Please try again in one minute.'
    }
  };
  function language() { return document.documentElement.lang === 'en' ? 'en' : 'ko'; }
  function loadChallenge() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.onload = function () { window.turnstile ? resolve(window.turnstile) : reject(new Error('unavailable')); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }
  document.querySelectorAll('form[data-inquiry-server]').forEach(function (form) {
    var button = form.querySelector('button[type="submit"]');
    var status = form.querySelector('[data-inquiry-status]');
    var container = form.querySelector('[data-inquiry-challenge]');
    var token = '', widget, challenge, busy = false, state = 'loading', reference = '';
    function show(next, id) {
      state = next; reference = id || '';
      status.textContent = copy[language()][state] + reference;
    }
    function setToken(value) { token = value; button.disabled = busy || !token; }
    button.disabled = true;
    show('loading');
    new MutationObserver(function () { show(state, reference); }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    fetch('/api/inquiry/config', { headers: { Accept: 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(10000) })
      .then(function (response) { if (!response.ok) throw new Error('unavailable'); return response.json(); })
      .then(function (config) {
        if (config.ready !== true || typeof config.siteKey !== 'string' || !config.siteKey) throw new Error('unavailable');
        return loadChallenge().then(function (api) {
          challenge = api;
          widget = api.render(container, {
            sitekey: config.siteKey, action: 'inquiry', language: language(),
            callback: function (value) { setToken(value); if (!busy && ['verify', 'loading', 'unavailable'].includes(state)) show('ready'); },
            'expired-callback': function () { setToken(''); if (!busy) show('verify'); },
            'error-callback': function () { setToken(''); if (!busy) show('unavailable'); }
          });
          show('verify');
        });
      }).catch(function () { setToken(''); show('unavailable'); });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (busy) return;
      if (!token) { show('verify'); return; }
      if (!form.reportValidity()) return;
      var data = Object.fromEntries(new FormData(form));
      data.privacy = form.elements.privacy.checked;
      data.turnstile_token = token;
      data.page = location.pathname;
      data.lang = language();
      busy = true; button.disabled = true; show('sending');
      fetch('/api/inquiry', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(data), signal: AbortSignal.timeout(25000)
      }).then(async function (response) {
        var result = await response.json();
        if (response.status === 429) { show('limited'); return; }
        if (response.status !== 202 || result.ok !== true || typeof result.id !== 'string' || !result.id) throw new Error('unconfirmed');
        form.reset(); show('sent', result.id);
      }).catch(function () { show('failed'); }).finally(function () {
        busy = false; setToken('');
        if (challenge && widget !== undefined) challenge.reset(widget);
      });
    });
  });
})();
