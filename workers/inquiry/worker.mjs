const SENDER = 'export@seoulcook.com';
const HOSTS = new Set(['seoulcook.com', 'www.seoulcook.com']);
const MAX_BYTES = 32768;
const ADDRESS = /^[^\s<>@\r\n]+@[^\s<>@\r\n]+\.[^\s<>@\r\n]+$/;

function recipients(env) {
  const values = JSON.parse(env.INQUIRY_RECIPIENTS || 'null');
  if (!Array.isArray(values) || values.length !== 2) throw new Error('Invalid configuration');
  const normalized = values.map(v => typeof v === 'string' ? v.trim().toLowerCase() : '');
  if (normalized.some(v => !ADDRESS.test(v) || v === SENDER) || new Set(normalized).size !== 2) {
    throw new Error('Invalid configuration');
  }
  return normalized;
}

function configured(env) {
  try {
    recipients(env);
    return env.INQUIRY_ENABLED === 'true' && Boolean(env.TURNSTILE_SITE_KEY && env.TURNSTILE_SECRET_KEY &&
      env.EMAIL?.send && env.INQUIRY_LIMITER?.limit);
  } catch { return false; }
}

function json(data, status = 200, extra = {}) {
  return Response.json(data, { status, headers: {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra,
  } });
}

async function boundedBody(request) {
  if (Number(request.headers.get('Content-Length')) > MAX_BYTES) throw new Error('too_large');
  const reader = request.body?.getReader();
  if (!reader) throw new Error('invalid');
  const chunks = []; let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_BYTES) { await reader.cancel(); throw new Error('too_large'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  const type = (request.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  if (type === 'application/json') return JSON.parse(text);
  if (type === 'application/x-www-form-urlencoded') return Object.fromEntries(new URLSearchParams(text));
  throw new Error('unsupported');
}

function validate(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('invalid');
  const field = (key, max, required = false, multiline = false) => {
    const raw = data[key] ?? '';
    if (typeof raw !== 'string' || raw.length > max || /\0/.test(raw) || (!multiline && /[\r\n]/.test(raw))) {
      throw new Error('invalid');
    }
    const value = raw.trim(); if (required && !value) throw new Error('invalid'); return value;
  };
  const result = { name: field('name', 100, true), email: field('email', 254, true),
    company: field('company', 200), country: field('country', 100), inquiry_type: field('inquiry_type', 100),
    message: field('message', 10000, true, true), token: field('turnstile_token', 2048, true),
    page: field('page', 30), lang: field('lang', 2) };
  if (!ADDRESS.test(result.email) || (data.privacy !== true && data.privacy !== 'on') || field('contact_url', 200)) {
    throw new Error('invalid');
  }
  if (!['/contact/', '/b2b/'].includes(result.page)) throw new Error('invalid');
  if (!['ko', 'en'].includes(result.lang)) result.lang = 'ko';
  return result;
}

function textMessage(input, id) {
  return ['SeoulCook Website Inquiry', 'Inquiry ID: ' + id, 'Page: ' + input.page,
    'Name: ' + input.name, 'Email: ' + input.email, 'Company: ' + input.company,
    'Country / Region: ' + input.country, 'Inquiry type: ' + input.inquiry_type,
    'Privacy consent: yes', '', input.message].join('\n');
}

export function createWorker({ fetchImpl = globalThis.fetch, uuid = () => crypto.randomUUID() } = {}) {
  return {
    async fetch(request, env) {
      const url = new URL(request.url);
      if (!HOSTS.has(url.hostname)) return json({ ok: false, code: 'not_found' }, 404);
      if (url.pathname === '/api/inquiry/config' && request.method === 'GET') {
        return configured(env) ? json({ ready: true, siteKey: env.TURNSTILE_SITE_KEY }) : json({ ready: false }, 503);
      }
      if (url.pathname !== '/api/inquiry') return json({ ok: false, code: 'not_found' }, 404);
      if (request.method !== 'POST') return json({ ok: false, code: 'method_not_allowed' }, 405, { Allow: 'POST' });
      if (request.headers.get('Origin') !== url.origin) return json({ ok: false, code: 'origin_rejected' }, 403);
      if (!configured(env)) return json({ ok: false, code: 'not_ready' }, 503);
      let input;
      try { input = validate(await boundedBody(request)); }
      catch (error) {
        const status = error.message === 'too_large' ? 413 : error.message === 'unsupported' ? 415 : 400;
        return json({ ok: false, code: 'invalid_request' }, status);
      }
      try {
        const ip = request.headers.get('CF-Connecting-IP');
        if (!ip) return json({ ok: false, code: 'not_ready' }, 503);
        const limit = await env.INQUIRY_LIMITER.limit({ key: ip });
        if (!limit.success) return json({ ok: false, code: 'rate_limited' }, 429, { 'Retry-After': '60' });
        const verification = await fetchImpl('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(10000),
          body: JSON.stringify({ secret: env.TURNSTILE_SECRET_KEY, response: input.token, remoteip: ip }),
        });
        const challenge = await verification.json();
        if (!verification.ok || challenge.success !== true || challenge.hostname !== url.hostname || challenge.action !== 'inquiry') {
          return json({ ok: false, code: 'verification_failed' }, 403);
        }
      } catch { return json({ ok: false, code: 'verification_unavailable' }, 503); }
      const id = uuid();
      try {
        const accepted = await env.EMAIL.send({ from: SENDER, to: recipients(env),
          replyTo: { email: input.email, name: input.name },
          subject: '[SeoulCook Website Inquiry] ' + (input.company || input.name),
          text: textMessage(input, id), headers: { 'X-SeoulCook-Inquiry-ID': id } });
        if (!accepted?.messageId) throw new Error('Missing provider acceptance');
        return json({ ok: true, id }, 202);
      } catch { return json({ ok: false, code: 'delivery_failed', id }, 502); }
    },

    async email(message, env) {
      if (message.to.toLowerCase() !== SENDER || message.headers.has('X-SeoulCook-Forwarded') || message.canBeForwarded === false) {
        message.setReject('This message cannot be forwarded.'); return;
      }
      const addresses = recipients(env);
      const headers = new Headers({ 'X-SeoulCook-Forwarded': '1' });
      const results = await Promise.allSettled(addresses.map(address => message.forward(address, headers)));
      if (results.some(result => result.status === 'rejected')) throw new Error('Required mail destination failed.');
    },
  };
}

export default createWorker();
