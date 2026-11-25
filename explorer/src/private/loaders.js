/* The dashboard's live datasets: GitHub connector answers reshaped into
   rows. Registered once, before the page first reads them. The pull request
   and issue datasets keep only the continuous improvement loop's own rows,
   by the rule the public document uses (evals/loop-activity.json,
   scripts/loop_activity.py). */
import LOOP from '../../../evals/loop-activity.json' with { type: 'json' };
import { ISSUE_REPOS } from '../core/display.js';

const names = (ls) => (ls || []).map((l) => (typeof l === 'string' ? l : l && l.name)).filter(Boolean);
const starts = (s, list) => typeof s === 'string' && list.some((p) => s.startsWith(p));
export const isLoopBranch = (b) => starts(b, LOOP.pull_branch_prefixes);
export const isLoopIssue = (title, labels) => starts(title, LOOP.issue_title_prefixes) || names(labels).some((n) => LOOP.issue_labels.includes(n));

/* A connector answer's JSON, from its first JSON text part when it has parts. */
const unwrap = (x, what) => {
  let b = x;
  if (b && Array.isArray(b.content)) { const t = b.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) b = t.text; }
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { throw new Error('GitHub answered with text, not ' + (what || 'results') + ': ' + b.slice(0, 160)); } }
  return b;
};

/* A GitHub search answer's items. */
const items = (answer) => {
  const a = unwrap(answer);
  if (!a || !Array.isArray(a.items)) throw new Error('GitHub search returned no items');
  return a.items;
};

export function registerLoaders(dash) {
  if (!dash || typeof dash.loader !== 'function') return;
  dash.loader('open_prs', {
    description: 'The GitHub search answer as one row per pull request, with the repo name taken from its address; then, per pull request, its head branch, its check runs and commit statuses summed up as one checks result, and any Claude session or Actions run link in its description',
    fn: async ({ answer, call }) => {
      const a = items(answer);
      // A check run that ended badly fails the PR; a cancelled one is usually superseded, so it is ignored.
      const BAD = new Set(['failure', 'timed_out', 'startup_failure', 'action_required']);
      const checksOf = (runs, status) => {
        const list = (runs && runs.check_runs) || [];
        const statuses = status && status.total_count > 0 ? status.statuses || [] : [];
        const failed = list.filter((r) => BAD.has(r.conclusion)).length + statuses.filter((x) => x.state === 'failure' || x.state === 'error').length;
        const running = list.filter((r) => r.status !== 'completed').length + statuses.filter((x) => x.state === 'pending').length;
        if (failed) return 'Failed: ' + failed;
        if (running) return 'In progress: ' + running;
        return list.length + statuses.length ? 'Passed' : 'No checks';
      };
      const rows = await Promise.all(a.map(async (p) => {
        const parts = String(p.repository_url || '').split('/');
        const owner = parts[parts.length - 2], repo = parts[parts.length - 1];
        const body = String(p.body || '');
        const session = (body.match(/claude\.ai\/code\/session_([A-Za-z0-9]+)/) || [])[1] || '';
        const run_url = (body.match(/https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/actions\/runs\/\d+/) || [])[0] || '';
        const q = { owner, repo, pullNumber: p.number };
        const [pr, runs, status] = await Promise.all(['get', 'get_check_runs', 'get_status']
          .map((method) => call('pull_request_read', { ...q, method }).then(unwrap, () => null)));
        return {
          repo, number: p.number, title: p.title,
          author: (p.user && p.user.login) || '', author_type: (p.user && p.user.type) || '', draft: !!p.draft,
          labels: names(p.labels).join(', '),
          created_at: p.created_at, updated_at: p.updated_at, url: p.html_url,
          branch: (pr && pr.head && pr.head.ref) || '', session, run_url,
          checks: runs || status ? checksOf(runs, status) : 'Unknown', checks_url: p.html_url + '/checks',
        };
      }));
      return rows.filter((r) => isLoopBranch(r.branch));
    },
  });
  dash.loader('merged_prs', {
    description: 'The GitHub search answer as one row per merged pull request, then its head branch; only the loop\'s',
    fn: async ({ answer, call }) => {
      const a = items(answer);
      const rows = await Promise.all(a.map(async (p) => {
        const parts = String(p.repository_url || '').split('/');
        const pr = await call('pull_request_read', { owner: parts[parts.length - 2], repo: parts[parts.length - 1], pullNumber: p.number, method: 'get' })
          .then(unwrap, () => null);
        return {
          repo: parts[parts.length - 1], number: p.number, title: p.title,
          author: (p.user && p.user.login) || '', closed_at: p.closed_at, url: p.html_url,
          branch: (pr && pr.head && pr.head.ref) || '',
        };
      }));
      return rows.filter((r) => isLoopBranch(r.branch));
    },
  });
  dash.loader('open_issues', {
    description: 'Open issues in each issue_repos repository (explorer/display.json), one row per issue; only the loop\'s',
    fn: async ({ answer, call, args }) => {
      const parse = (x) => {
        const a = unwrap(x, 'issues');
        if (!a || !Array.isArray(a.issues)) throw new Error('GitHub returned no issues list');
        return a.issues;
      };
      // The dataset's own read (datasets.json, written by build.js from issue_repos) is the first repository.
      const rows = [];
      for (const full of ISSUE_REPOS) {
        const [owner, repo] = full.split('/');
        const list = parse(full === ISSUE_REPOS[0] ? answer : await call('list_issues', { ...args, owner, repo }));
        for (const i of list) if (isLoopIssue(i.title, i.labels)) rows.push({
          repo, number: i.number, title: i.title,
          labels: names(i.labels).join(', '),
          created_at: i.created_at, updated_at: i.updated_at,
          url: 'https://github.com/' + full + '/issues/' + i.number,
        });
      }
      return rows;
    },
  });
  dash.loader('eval_ingests', {
    description: 'Commits on the results branch as rows: the run id each one saved, when, and its link',
    fn: ({ answer }) => {
      const a = unwrap(answer, 'commits');
      if (!Array.isArray(a)) throw new Error('GitHub returned no commit list');
      return a.map((c) => {
        const msg = (c.commit && c.commit.message) || '';
        const m = msg.match(/routine run (\d{8}T\d{6}Z-[0-9a-f]{6})/);
        return { sha: c.sha, run_id: m ? m[1] : null, message: msg.split('\n')[0], ingested_at: c.commit && c.commit.committer && c.commit.committer.date, url: c.html_url };
      });
    },
  });
}
