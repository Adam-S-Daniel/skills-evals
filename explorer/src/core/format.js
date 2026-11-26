/* Pure helpers: cleaning, links, model names and dates in the display zone (explorer/display.json). */
import { STRINGS } from './strings.js';
import { ZONE_ABBR, fmt as inZone } from './zone.js';

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
  const opts = { month: 'short', day: 'numeric' };
  const year = (t) => inZone(t, { year: 'numeric' });
  if (isFinite(refMs) && year(ms) !== year(refMs)) opts.year = 'numeric';
  return inZone(ms, opts);
}

export function fmtDateTime(ms) {
  if (!isFinite(ms)) return STRINGS.unknown;
  return inZone(ms, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) + ' ' + ZONE_ABBR;
}

/* The calendar day in the display zone of a moment, as a 'YYYY-MM-DD' key. */
const ISO_DAY = { year: 'numeric', month: '2-digit', day: '2-digit' };
export function etDayKey(ms) {
  if (!isFinite(ms)) return null;
  const parts = inZone(ms, ISO_DAY, null, 'en-CA');
  return /^\d{4}-\d{2}-\d{2}$/.test(parts) ? parts : null;
}

/* A clock time alone, '7:39 PM', for a list already grouped by day. */
export function fmtTime(ms) {
  if (!isFinite(ms)) return STRINGS.unknown;
  return inZone(ms, { hour: 'numeric', minute: '2-digit' });
}

/* The only place this page reads or writes a calendar field of a date. A view
   never calls toISOString, getUTC* or Intl.DateTimeFormat itself: the date guard
   in test/run.js fails the build if it does. A day or week key is the
   'YYYY-MM-DD' the data buckets by (a UTC day, or the UTC Monday of a week). */
const DAY_MS = 86400000;
export const dayKeyMs = (key) => (typeof key === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(key) ? Date.parse(key + 'T00:00:00Z') : NaN);
export const isDayKey = (key) => isFinite(dayKeyMs(key));

/* A calendar day the data names without a time ('2026-11-10'), shown as that
   day in the display zone: read at noon, so no zone moves it to another date. */
export function fmtCalendarDay(key, refMs) {
  return isDayKey(key) ? fmtDay(dayKeyMs(key) + 12 * 3600 * 1000, refMs) : STRINGS.unknown;
}

/* The day key of an instant, and of the Monday that starts its week. */
export function dayKeyOf(ms) {
  return isFinite(ms) ? new Date(ms).toISOString().slice(0, 10) : null;
}
export function weekKeyOf(ms) {
  if (!isFinite(ms)) return null;
  const d = new Date(ms);
  return dayKeyOf(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - ((d.getUTCDay() + 6) % 7)));
}
/* Every day key from `first` to `last`, so a day without data shows as a gap. */
export function dayKeysBetween(first, last) {
  const out = [];
  if (!isDayKey(first) || !isDayKey(last)) return out;
  for (let t = dayKeyMs(first); t <= dayKeyMs(last); t += DAY_MS) out.push(dayKeyOf(t));
  return out;
}

/* "Nov 12", with the year only when it differs from the reference's. */
export function fmtDayKey(key, refMs) {
  return isDayKey(key) ? fmtUtcDay(dayKeyMs(key), refMs) : STRINGS.unknown;
}
/* "Mon Nov 9" for the row of a week, "week of Mon Nov 9" inside a sentence. */
export function fmtWeekStart(key, refMs) {
  if (!isDayKey(key)) return STRINGS.unknown;
  const wd = inZone(dayKeyMs(key), { weekday: 'short' }, 'UTC');
  return wd + ' ' + fmtUtcDay(dayKeyMs(key), refMs);
}
export const fmtWeekOf = (key, refMs) => STRINGS.weekOf(fmtWeekStart(key, refMs));

/* "Monday noon ET": the weekday and clock time of an instant in the display zone. */
export function fmtResetLabel(ms) {
  if (!isFinite(ms)) return STRINGS.unknown;
  const f = (o) => inZone(ms, o);
  const clock = f({ hour: 'numeric', minute: '2-digit', hour12: false });
  return f({ weekday: 'long' }) + ' ' + (clock === '12:00' ? 'noon' : f({ hour: 'numeric', minute: '2-digit' })) + ' ' + ZONE_ABBR;
}

/* "06:53" on the UTC clock as a display-zone clock time ("1:53 AM ET"), using the
   offset in force on the reference day (daylight saving moves it), with `shift`: -1 when the zone's time falls on the day before the
   UTC one (02:00 UTC is 9:00 PM ET the evening before), 1 when on the day
   after it, else 0. */
export function utcClockToEt(hour, minute, refMs) {
  const base = isFinite(refMs) ? new Date(refMs) : new Date(0);
  const at = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate(), Number(hour), Number(minute)));
  const key = (zone) => inZone(at, ISO_DAY, zone, 'en-CA');
  const local = key(), utc = key('UTC');
  return { text: inZone(at, { hour: 'numeric', minute: '2-digit' }) + ' ' + ZONE_ABBR, shift: local === utc ? 0 : local < utc ? -1 : 1 };
}
const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/* "Oct 30 at 16:57 UTC" as the moment it names, in the display zone: the date and the
   clock, each in the offset in force then (daylight saving moves it). The year is
   the reference's, or the one before when that day is still ahead of the reference.
   Null when the month is not one. */
export function utcMomentToEt(mon, day, hour, minute, refMs) {
  const idx = MONTH_ABBR.indexOf(String(mon).charAt(0).toUpperCase() + String(mon).slice(1, 3).toLowerCase());
  if (idx < 0) return null;
  const year = isFinite(refMs) ? new Date(refMs).getUTCFullYear() : 2001;
  const on = (y) => Date.UTC(y, idx, Number(day), Number(hour), Number(minute));
  let at = on(year);
  if (isFinite(refMs) && at > refMs) at = on(year - 1);
  const f = (o) => inZone(at, o);
  return { date: f({ month: 'short', day: 'numeric' }), clock: f({ hour: 'numeric', minute: '2-digit' }) + ' ' + ZONE_ABBR,
    named: MONTH_ABBR[idx] + ' ' + Number(day) };
}

/* A UTC calendar day (a census window edge, which is a UTC Monday), shown
   as that day rather than shifted into the display zone. */
export function fmtUtcDay(ms, refMs) {
  if (!isFinite(ms)) return STRINGS.unknown;
  const opts = { month: 'short', day: 'numeric' };
  if (isFinite(refMs) && new Date(ms).getUTCFullYear() !== new Date(refMs).getUTCFullYear()) opts.year = 'numeric';
  return inZone(ms, opts, 'UTC');
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
