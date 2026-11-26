import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../assets/js/inquiry.js', import.meta.url), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
async function setup({ configReady = true, responseStatus = 202, result = { ok: true, id: 'test-reference' }, fail = false } = {}) {
  let handler, options, resets = 0, calls = [], resolveSend, observer;
  const button = { disabled: false }, status = { textContent: '' }, root = { lang: 'ko' };
  const form = { elements: { privacy: { checked: true } }, reportValidity: () => true,
    reset: () => { resets++; }, addEventListener: (_, callback) => { handler = callback; },
    querySelector: selector => selector.includes('submit') ? button : selector.includes('status') ? status : {} };
  const challenge = { render: (_, config) => { options = config; return 'widget'; }, reset: () => {} };
  const context = {
    window: { turnstile: challenge }, document: { documentElement: root, querySelectorAll: () => [form] },
    MutationObserver: class { constructor(callback) { observer = callback; } observe() {} },
    FormData: class { *[Symbol.iterator]() { yield ['name', 'Test']; yield ['email', 'sender@example.net']; yield ['message', 'Message']; } },
    location: { pathname: '/contact/' }, AbortSignal,
    fetch: async (url, init) => {
      calls.push({ url, init });
      if (url.endsWith('/config')) return { ok: configReady, json: async () => ({ ready: configReady, siteKey: 'public-key' }) };
      await new Promise(resolve => { resolveSend = resolve; });
      if (fail) throw new Error('offline');
      return { status: responseStatus, json: async () => result };
    }
  };
  vm.runInNewContext(source, context); await tick();
  return { button, status, calls, root, token: () => options.callback('verified-token'),
    submit: () => handler({ preventDefault() {} }), finish: async () => { resolveSend(); await tick(); },
    resets: () => resets, changeLanguage: () => { root.lang = 'en'; observer(); } };
}
test('client blocks sending until configuration and verification are ready', async () => {
  const app = await setup(); assert.equal(app.button.disabled, true);
  app.submit(); assert.equal(app.calls.length, 1);
  app.token(); assert.equal(app.button.disabled, false);
  app.submit(); app.submit(); assert.equal(app.calls.length, 2);
  const body = JSON.parse(app.calls[1].init.body);
  assert.equal(body.privacy, true); assert.equal(body.page, '/contact/');
  assert.equal(body.turnstile_token, 'verified-token'); assert.equal(body.lang, 'ko');
  await app.finish(); assert.equal(app.resets(), 1);
  assert.match(app.status.textContent, /test-reference/);
  app.token(); assert.match(app.status.textContent, /test-reference/);
});
test('client keeps entries on provider failure, without claiming success', async () => {
  const app = await setup({ responseStatus: 502, result: { ok: false } });
  app.token(); app.submit(); await app.finish();
  assert.equal(app.resets(), 0); assert.match(app.status.textContent, /접수를 확인하지/);
  assert.equal(app.button.disabled, true);
});
test('network failure preserves entries and warns against duplicate delivery', async () => {
  const app = await setup({ fail: true }); app.token(); app.submit(); await app.finish();
  assert.equal(app.resets(), 0); assert.match(app.status.textContent, /중복 전송/);
});
test('successful HTTP status without a valid acceptance receipt is not a success', async () => {
  const app = await setup({ result: { ok: true } }); app.token(); app.submit(); await app.finish();
  assert.equal(app.resets(), 0); assert.match(app.status.textContent, /접수를 확인하지/);
});
test('unavailable backend leaves direct email guidance and no enabled submit button', async () => {
  const app = await setup({ configReady: false });
  assert.equal(app.button.disabled, true); assert.match(app.status.textContent, /export@seoulcook.com/);
});
test('live status follows the KO/EN language choice and rate limiting preserves entries', async () => {
  const app = await setup({ responseStatus: 429, result: { ok: false } });
  app.changeLanguage(); assert.match(app.status.textContent, /security check/);
  app.token(); app.submit(); await app.finish();
  assert.equal(app.resets(), 0); assert.match(app.status.textContent, /one minute/);
});
