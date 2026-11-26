/* Words about the display zone (explorer/display.json), computed from it with
   Intl so no label or sentence names a zone by hand. Pure and deterministic:
   the zone's two seasons are probed at fixed Mondays, never at the current time. */
import { TIME_ZONE } from './display.js';

const WINTER = Date.UTC(2026, 0, 12), SUMMER = Date.UTC(2026, 6, 13);
/* An instant formatted in the display zone (or `zone`), with Intl options and locale (en-US unless given). */
export const fmt = (ms, o, zone, locale) => new Intl.DateTimeFormat(locale || 'en-US', { timeZone: zone || TIME_ZONE, ...o }).format(new Date(ms));
/* "ET": the locale's short name for the zone, the same all year (the part after the date). */
const abbr = (style) => fmt(WINTER, { timeZoneName: style }).split(', ').pop();
export const ZONE_ABBR = (() => { try { return abbr('shortGeneric'); } catch { return abbr('short'); } })();

/* "7 PM", "5:30 AM" or "noon" of an instant in the zone. */
const clock = (ms) => {
  const t = fmt(ms, { hourCycle: 'h23', hour: 'numeric', minute: '2-digit' });
  return t === '12:00' ? 'noon' : fmt(ms, { hour: 'numeric', minute: t.endsWith(':00') ? undefined : '2-digit' });
};
const day = (ms, zone) => fmt(ms, { dateStyle: 'short' }, zone);
const before = (ms) => (day(ms) === day(ms, 'UTC') ? '' : ' the evening before');
/* Minus the zone's offset from UTC at an instant, in ms ("GMT-05:00" is +5 hours): Date reads the offset as a time zone
   designator. A zone with no offset in its name (UTC) gives NaN, which `seasons` reads as one season. */
const off = (ms) => Date.parse('1970-01-01T00:00' + /[+-]\d\d:\d\d/.exec(fmt(ms, { timeZoneName: 'longOffset' })));
/* A UTC hour on a Monday as [standard, daylight] instants, or [only] when the offset never changes. */
const seasons = (utcHour) => {
  const a = WINTER + utcHour * 36e5, b = SUMMER + utcHour * 36e5, d = off(a) - off(b);
  return d ? (d > 0 ? [a, b] : [b, a]) : [a];
};
const paren = (words) => ' (' + words + ' during daylight saving time)';

/* "7 PM ET the evening before (8 PM during daylight saving time)": when a UTC day starts. */
export const utcDayStartWords = () => {
  const [s, d] = seasons(0);
  return clock(s) + ' ' + ZONE_ABBR + before(s) + (d ? paren(clock(d)) : '');
};

/* "Monday at noon ET (1 PM during daylight saving time)": when a spend week starts (Monday 17:00 UTC). */
export const spendWeekStartWords = () => {
  const [s, d] = seasons(17);
  return fmt(s, { weekday: 'long' }) + ' at ' + clock(s) + ' ' + ZONE_ABBR + (d ? paren(clock(d)) : '');
};
