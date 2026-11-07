/* The functions and constants the page exposes to tests, with no side
   effects, shared by both entries. */
import { SCHEMA_VERSION, WINDOW_WEEKS, MIN_PAIRED_RUNS, HELPS_MIN_GAIN, WORSE_TOLERANCE } from '../core/rules.js';
import { STRINGS, useVoice } from '../core/strings.js';
import { GLOSSES, GLOSS_MISSING, HOOK_GLOSSES } from '../core/glosses.js';
import { clean, githubLink, friendlyModel, fmtDay, fmtDateTime, fmtCount, wordsFor } from '../core/format.js';
import { validateDoc } from '../core/validate.js';
import { VERDICT_CHIPS, poolRuns, chipFor, sentenceFor, weeklyGains, gainPerKb, hasRegression } from '../core/stats.js';
import { h, textOf, findAll, toDom } from '../core/h.js';
import { purposeOf, skillItems, sectionItems, wholeGuidance } from '../core/items.js';
import { DEFAULT_DATA_URL, allowedDataUrl, dataUrlFromSearch, cacheBust, loadData } from '../adapters/web.js';
import { trendChart } from '../views/trend.js';
import { hasAlone, legendFor } from '../views/models.js';
import { sectionCard } from '../views/cards.js';
import { confidenceView, clipName } from '../views/range.js';
import { alertText } from '../views/alerts.js';
import { lessonTitle, lessonItem, lessonIssue, lessonsView } from '../views/lessons.js';
import { buildPage, renderRoute } from '../views/page.js';
import { parseRoute, hashFor, groupOf, GROUPS } from '../core/route.js';
import { hookItems, hookWeeks, blockedThisWeek, mondayOf } from '../core/hooks.js';
import { fixtureQueue } from '../core/fixtures.js';
import { searchItems, filterItems } from '../views/search.js';
import { checkWeeks } from '../views/hooks.js';
import { prWeeks } from '../views/impact.js';
import { runsOf } from '../views/subject.js';
import { LOOP_TITLE } from '../views/loop.js';
import { buildFailure } from '../views/failure.js';

/* What tool/test/run.js reads from the built page, run in a Node sandbox
   that defines `module`. */
export const EXPORTS = {
  SCHEMA_VERSION, WINDOW_WEEKS, MIN_PAIRED_RUNS, VERDICT_CHIPS, HELPS_MIN_GAIN, WORSE_TOLERANCE, DEFAULT_DATA_URL,
  STRINGS, GLOSSES, GLOSS_MISSING, purposeOf,
  clean, githubLink, friendlyModel, alertText, fmtDay, fmtDateTime, fmtCount, wordsFor,
  allowedDataUrl, dataUrlFromSearch, cacheBust, validateDoc, loadData,
  poolRuns, trendChart, chipFor, sentenceFor, weeklyGains, gainPerKb, hasRegression, hasAlone, legendFor, sectionCard,
  skillItems, sectionItems, wholeGuidance, lessonTitle, lessonItem, lessonIssue, lessonsView, buildPage, renderRoute, buildFailure, confidenceView, clipName, h, textOf, findAll, toDom,
  useVoice, HOOK_GLOSSES, parseRoute, hashFor, groupOf, GROUPS, hookItems, hookWeeks, blockedThisWeek, mondayOf, checkWeeks,
  fixtureQueue, searchItems, filterItems, prWeeks, runsOf, LOOP_TITLE
};
