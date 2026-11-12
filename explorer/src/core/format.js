/* Pure helpers: cleaning, links, model names and US Eastern dates. */
import { STRINGS } from './strings.js';
import { TIME_ZONE } from './rules.js';

export const UNSAFE = /\S*(?:@|\/home\/|\/Users\/|\/root\/|\/tmp\/|cse_|session_|[A-Za-z]:\\)\S*/g;

export function clean(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(UNSAFE, STRINGS.hidden);
}

export function githubLink(url) {
  if (typeof url !== 'string' || !url.startsWith('https://github.com/')) return null;
  let parsed;
  try { parsed = new URL(url); } catch (e) { return null; }
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'github.com' || parsed.username || parsed.password || parsed.port) return null;
  return parsed.href;
}

export function friendlyModel(id) {
  const raw = String(id || '').toLowerCase();
  if (!/^[a-z0-9-]+$/.test(raw)) return clean(id) || STRINGS.unknown;
  const parts = raw.split('-').filter((p) => p && !/^\d{8}$/.test(p));
  const words = [];
  const nums = [];
  for (const p of parts) {
    if (/^\d+$/.test(p)) nums.push(p);
    else {
      if (nums.length) { words.push(nums.join('.')); nums.length = 0; }
      words.push(p.charAt(0).toUpperCase() + p.slice(1));
    }
  }
  if (nums.length) words.push(nums.join('.'));
  return words.join(' ');
}

export function parseTime(s) {
  if (typeof s !== 'string') return NaN;
  return Date.parse(s);
}

export function fmtDay(ms, refMs) {
  if (!isFinite(ms)) return STRINGS.unknown;
  const opts = { timeZone: TIME_ZONE, month: 'short', day: 'numeric' };
  const year = (t) => new Intl.DateTimeFormat('en-US', { timeZone: TIME_ZONE, year: 'numeric' }).format(new Date(t));
  if (isFinite(refMs) && year(ms) !== year(refMs)) opts.year = 'numeric';
  return new Intl.DateTimeFormat('en-US', opts).format(new Date(ms));
}

export function fmtDateTime(ms) {
  if (!isFinite(ms)) return STRINGS.unknown;
  const s = new Intl.DateTimeFormat('en-US', {
    timeZone: TIME_ZONE, month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit'
  }).format(new Date(ms));
  return s + ' ' + STRINGS.et;
}

/* A UTC calendar day (a census window edge, which is a UTC Monday), shown
   as that day rather than shifted into Eastern time. */
export function fmtUtcDay(ms, refMs) {
  if (!isFinite(ms)) return STRINGS.unknown;
  const opts = { timeZone: 'UTC', month: 'short', day: 'numeric' };
  if (isFinite(refMs) && new Date(ms).getUTCFullYear() !== new Date(refMs).getUTCFullYear()) opts.year = 'numeric';
  return new Intl.DateTimeFormat('en-US', opts).format(new Date(ms));
}

/* Dollars with thousands separators and cents: $5,541.65. The one place that
   formats money, so no view prints "$5541.65". */
export function fmtUsd(x) {
  return '$' + Number(x).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtCount(x) {
  const n = Number(x) || 0;
  const r = Math.round(n);
  if (Math.abs(n - r) < 1e-6) return String(r);
  return n.toFixed(1);
}

export function fmtRate(p, t) {
  if (!(t > 0)) return '0%';
  return Math.round((p / t) * 100) + '%';
}

export function fmtGain(g) {
  if (g === null || !isFinite(g)) return STRINGS.unknown;
  const p = Math.round(g * 100);
  if (p === 0) return STRINGS.gainZero;
  return p > 0 ? STRINGS.gainUp(p) : STRINGS.gainDown(-p);
}

export function wordsFor(bytes) {
  const w = Math.max(10, Math.round((Number(bytes) || 0) / 6 / 10) * 10);
  return w;
}

/* A figure to 2 decimals for display only (the data keeps full precision);
   a real minus sign, and never "-0.00". */
export function fmt2(x) {
  if (typeof x !== 'number' || !isFinite(x)) return STRINGS.noValue;
  const s = Math.abs(x).toFixed(2);
  return x < 0 && Number(s) !== 0 ? '−' + s : s;
}

/* The same with an explicit plus sign for a gain: +0.17, 0.00, −0.10. */
export function fmtSigned2(x) {
  const s = fmt2(x);
  return typeof x === 'number' && isFinite(x) && x > 0 && s !== '0.00' ? '+' + s : s;
}

/* Text from outside the page with every long decimal rounded to 2 places,
   for sentences the data still words itself. */
export function roundDecimals(text) {
  return String(text).replace(/\d+\.\d{3,}/g, (m) => Number(m).toFixed(2));
}
