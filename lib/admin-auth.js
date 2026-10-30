import { neon } from '@neondatabase/serverless';
import { createHmac, pbkdf2Sync, scryptSync, timingSafeEqual } from 'node:crypto';

export function db() {
  const url = process.env.DATABASE_URL;
  if (!url || !/^postgres(?:ql)?:\/\//.test(url)) return null;
  return neon(url);
}
export function isConfigured() {
  return !!(db() && (process.env.DPARRANDA_ADMIN_PASSWORD_PBKDF2 || process.env.DPARRANDA_ADMIN_PASSWORD_SCRYPT) && process.env.DPARRANDA_SESSION_SECRET && process.env.DPARRANDA_SESSION_SECRET.length >= 32);
}
export function json(res, status, data) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'private, no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.status(status).end(JSON.stringify(data));
}
function mac(value) {
  return createHmac('sha256', process.env.DPARRANDA_SESSION_SECRET).update(value).digest('base64url');
}
function tokenValid(token) {
  if (!token || token.length > 512) return false;
  const [payload, signature] = token.split('.');
  if (!payload || !signature || !/^[A-Za-z0-9_-]+$/.test(payload)) return false;
  const expected = mac(payload);
  if (signature.length !== expected.length) return false;
  if (!timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return false;
  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    return data.role === 'admin' && Number.isFinite(data.exp) && data.exp > Date.now() && data.exp < Date.now() + 12 * 3600_000 + 60_000;
  } catch { return false; }
}
export function authenticated(req) {
  if (!isConfigured()) return false;
  const match = String(req.headers.cookie || '').match(/(?:^|;\s*)dp_admin=([^;]+)/);
  return tokenValid(match && match[1]);
}
export function setSession(res, enabled) {
  if (!enabled) {
    res.setHeader('Set-Cookie', 'dp_admin=; HttpOnly; Secure; SameSite=Strict; Path=/api/admin; Max-Age=0');
    return;
  }
  const payload = Buffer.from(JSON.stringify({ role: 'admin', exp: Date.now() + 12 * 3600_000 }), 'utf8').toString('base64url');
  const token = payload + '.' + mac(payload);
  res.setHeader('Set-Cookie', 'dp_admin=' + token + '; HttpOnly; Secure; SameSite=Strict; Path=/api/admin; Max-Age=43200');
}
export function passwordValid(value) {
  if (typeof value !== 'string' || value.length < 12 || value.length > 256) return false;
  // New administrator credentials can be generated entirely in the browser,
  // without disclosing the plaintext password to a third-party hash service.
  const p = String(process.env.DPARRANDA_ADMIN_PASSWORD_PBKDF2 || '').split(':');
  if (p.length === 4 && p[0] === 'pbkdf2-sha256') {
    const iterations = Number(p[1]);
    if (iterations !== 600000 || !/^[0-9a-f]{32}$/i.test(p[2]) || !/^[0-9a-f]{64}$/i.test(p[3])) return false;
    const calculated = pbkdf2Sync(value, Buffer.from(p[2], 'hex'), iterations, 32, 'sha256');
    const expected = Buffer.from(p[3], 'hex');
    return timingSafeEqual(calculated, expected);
  }
  // Compatibility with previously provisioned, server-side scrypt credentials.
  const parts = String(process.env.DPARRANDA_ADMIN_PASSWORD_SCRYPT || '').split(':');
  if (parts.length !== 2 || !/^[0-9a-f]{32,128}$/i.test(parts[0]) || !/^[0-9a-f]{128}$/i.test(parts[1])) return false;
  const calculated = scryptSync(value, Buffer.from(parts[0], 'hex'), 64);
  const expected = Buffer.from(parts[1], 'hex');
  return timingSafeEqual(calculated, expected);
}
export function sameOrigin(req) {
  const origin = String(req.headers.origin || '');
  if (!origin) return false;
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  if (!host || typeof host !== 'string') return false;
  return origin === 'https://' + host || (process.env.NODE_ENV !== 'production' && origin === 'http://' + host);
}
export function safeText(x, max=250) {
  return typeof x === 'string' ? x.trim().slice(0, max) : '';
}
export function validLocalDate(s) { return s === null || s === '' || (typeof s === 'string' && /^20\d{2}-(0[1-9]|1[0-2])-([0-2]\d|3[01])$/.test(s) && !Number.isNaN(Date.parse(s + 'T12:00:00Z')) && new Date(s + 'T12:00:00Z').toISOString().slice(0,10)===s); }
