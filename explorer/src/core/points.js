/* Spend drawn from the weekly Max allowance, shown only as approximate points
   (percent of the weekly allowance), never list-price dollars. The rates are
   the document's `spend.rates` (dashboard/build.py writes them from
   evals/points.yml and the account meter); this module holds no rate of its
   own, so with none a figure reads as no value. Spend paid from the monthly
   API credit never comes through here. */
import { STRINGS } from './strings.js';
import { fmtUsd } from './format.js';
import { h } from './h.js';

const RATES = {};
const positive = (x) => (typeof x === 'number' && isFinite(x) && x > 0 ? x : null);

/* Read the rates from a document; every render calls it before drawing. */
export function useRates(doc) {
  const r = (doc && doc.spend && doc.spend.rates) || {};
  RATES.eval = positive(r.eval_usd_per_point);
  RATES.scheduled = positive(r.scheduled_task_usd_per_point);
  RATES.thread = positive(r.thread_usd_per_point);
}

/* Points for dollars of one kind ('eval', 'scheduled' or 'thread'), full precision; null without a rate or a number. */
export const toPoints = (usd, kind) => (RATES[kind] && typeof usd === 'number' && isFinite(usd) ? usd / RATES[kind] : null);

/* "≈12.3 points"; two decimals under one point, so a small eval run does not read as zero. */
export const fmtPoints = (p) => (p === null ? STRINGS.noValue : STRINGS.pointsApprox(p.toFixed(Math.abs(p) < 1 ? 2 : 1)));

/* Allowance spend as text, and as a cell whose tooltip names the rate behind it. */
export const spendText = (usd, kind) => fmtPoints(toPoints(usd, kind));
export function spendCell(usd, kind) {
  const p = toPoints(usd, kind);
  return p === null ? STRINGS.noValue : h('span', { title: STRINGS.pointsTip[kind](fmtUsd(RATES[kind])) }, fmtPoints(p));
}
