import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorker } from '../workers/inquiry/worker.mjs';

const targets = ['owner@example.net', 'team@example.org'];
const input = { name: '서울쿡 문의 테스트', email: 'buyer@example.net', company: 'Example Buyer',
  message: '소스 상품 견적을 문의합니다.', inquiry_type: 'Product question', privacy: true,
  turnstile_token: 'test-token', page: '/contact/', lang: 'ko' };

function setup({ verify = {}, sendFails = false } = {}) {
  const sent = []; const verified = []; const forwards = [];
  const env = { INQUIRY_ENABLED: 'true', INQUIRY_RECIPIENTS: JSON.stringify(targets),
    TURNSTILE_SITE_KEY: 'test-site-key', TURNSTILE_SECRET_KEY: 'private-test-key',
    INQUIRY_LIMITER: { limit: async () => ({ success: true }) },
    EMAIL: { send: async payload => { sent.push(payload); if (sendFails) throw new Error('private error'); return { messageId: 'accepted-id' }; } } };
  const worker = createWorker({ fetchImpl: async (url, options) => {
    verified.push({ url, options });
    return Response.json({ success: true, hostname: 'seoulcook.com', action: 'inquiry', ...verify });
  }, uuid: () => '29ac0c31-55dc-4bae-b72a-bf66d6a8fa7c' });
  return { worker, env, sent, verified, forwards };
}
function request(data = input, origin = 'https://seoulcook.com') {
  const headers = { 'Content-Type': 'application/json', 'CF-Connecting-IP': '192.0.2.10' };
  if (origin) headers.Origin = origin;
  return new Request('https://seoulcook.com/api/inquiry', { method: 'POST', headers, body: JSON.stringify(data) });
}

test('one inquiry is addressed to both configured recipients, never client-supplied targets', async () => {
  const s = setup(); const r = await s.worker.fetch(request({ ...input, to: 'attacker@example.com' }), s.env);
  assert.equal(r.status, 202); assert.equal(s.sent.length, 1);
  assert.deepEqual(s.sent[0].to, targets); assert.equal(s.sent[0].from, 'export@seoulcook.com');
  assert.equal(s.sent[0].replyTo.email, input.email); assert.match(s.sent[0].text, /소스 상품/);
  const body = await r.text(); assert(!body.includes(targets[0])); assert(!body.includes('private-test-key'));
});
test('missing runtime configuration fails closed without sending', async () => {
  const s = setup(); delete s.env.INQUIRY_RECIPIENTS;
  assert.equal((await s.worker.fetch(request(), s.env)).status, 503); assert.equal(s.sent.length, 0);
});
test('disabled rollout cannot accept public submissions', async () => {
  const s = setup(); s.env.INQUIRY_ENABLED = 'false';
  assert.equal((await s.worker.fetch(request(), s.env)).status, 503); assert.equal(s.sent.length, 0);
});
test('cross-origin and missing-Origin requests are refused before verification', async () => {
  const s = setup();
  for (const origin of ['https://evil.example', null]) assert.equal((await s.worker.fetch(request(input, origin), s.env)).status, 403);
  assert.equal(s.sent.length, 0); assert.equal(s.verified.length, 0);
});
test('privacy consent, required fields and header-injection protection are enforced server-side', async () => {
  const s = setup();
  for (const data of [{ ...input, privacy: false }, { ...input, name: '' }, { ...input, message: '' },
    { ...input, email: 'buyer@example.net\r\nBcc: attacker@example.com' }, { ...input, company: 'Buyer\r\nSubject: bad' },
    { ...input, contact_url: 'https://spam.example' }]) {
    assert.equal((await s.worker.fetch(request(data), s.env)).status, 400);
  }
  assert.equal(s.sent.length, 0);
});
test('invalid, wrong-host and wrong-action Turnstile results never send email', async () => {
  for (const verify of [{ success: false }, { hostname: 'evil.example' }, { action: 'other' }]) {
    const s = setup({ verify }); assert.equal((await s.worker.fetch(request(), s.env)).status, 403); assert.equal(s.sent.length, 0);
  }
});
test('rate limit is applied before the Turnstile API and mail service', async () => {
  const s = setup(); s.env.INQUIRY_LIMITER.limit = async () => ({ success: false });
  const r = await s.worker.fetch(request(), s.env);
  assert.equal(r.status, 429); assert.equal(s.verified.length, 0); assert.equal(s.sent.length, 0);
});
test('actual oversized bodies are rejected even without a Content-Length header', async () => {
  const s = setup(); const r = await s.worker.fetch(request({ ...input, message: 'x'.repeat(70000) }), s.env);
  assert.equal(r.status, 413); assert.equal(s.sent.length, 0);
});
test('mail-provider errors never become a success response or expose private details', async () => {
  const s = setup({ sendFails: true }); const r = await s.worker.fetch(request(), s.env);
  assert.equal(r.status, 502); assert(!(await r.text()).includes('private error'));
});
test('config exposes only a public challenge key, never recipients or secrets', async () => {
  const s = setup(); const r = await s.worker.fetch(new Request('https://seoulcook.com/api/inquiry/config'), s.env);
  assert.equal(r.status, 200); assert.deepEqual(await r.json(), { ready: true, siteKey: 'test-site-key' });
});
test('bad recipient sets, duplicates and export-to-itself loops fail closed', async () => {
  for (const recipients of [[], [targets[0]], [targets[0], targets[0]], ['export@seoulcook.com', targets[0]]]) {
    const s = setup(); s.env.INQUIRY_RECIPIENTS = JSON.stringify(recipients);
    assert.equal((await s.worker.fetch(request(), s.env)).status, 503); assert.equal(s.sent.length, 0);
  }
});
test('direct export email is forwarded to both recipients preserving the original message', async () => {
  const s = setup(); const calls = [];
  const message = { to: 'export@seoulcook.com', canBeForwarded: true, headers: new Headers(),
    forward: async (to, headers) => { calls.push({ to, marker: headers.get('X-SeoulCook-Forwarded') }); },
    setReject: reason => assert.fail(reason) };
  await s.worker.email(message, s.env); assert.deepEqual(calls.map(c => c.to), targets);
  assert(calls.every(c => c.marker === '1'));
});
test('both forwarding attempts run and any destination failure is reported', async () => {
  const s = setup(); const calls = [];
  const message = { to: 'export@seoulcook.com', headers: new Headers(),
    forward: async to => { calls.push(to); if (to === targets[0]) throw new Error('private mailbox detail'); },
    setReject: () => {} };
  await assert.rejects(s.worker.email(message, s.env), /Required mail destination failed/);
  assert.deepEqual(calls, targets);
});
test('loop-marked and unrelated inbound messages are rejected, never forwarded', async () => {
  const s = setup();
  for (const [to, headers] of [['other@seoulcook.com', new Headers()],
    ['export@seoulcook.com', new Headers({ 'X-SeoulCook-Forwarded': '1' })]]) {
    let rejected = false;
    await s.worker.email({ to, headers, setReject: () => { rejected = true; }, forward: () => assert.fail('unexpected forward') }, s.env);
    assert(rejected);
  }
});
