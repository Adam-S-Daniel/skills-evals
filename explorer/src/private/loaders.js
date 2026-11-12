/* The dashboard's live datasets: GitHub connector answers reshaped into
   rows. Registered once, before the page first reads them. */
export function registerLoaders(dash) {
  if (!dash || typeof dash.loader !== 'function') return;
  dash.loader('open_prs', {
    description: 'The GitHub search answer as one row per pull request, with the repo name taken from its address; then, per pull request, its head branch, its check runs and commit statuses summed up as one checks result, and any Claude session or Actions run link in its description',
    fn: async ({ answer, call }) => {
      let a = answer;
      if (a && Array.isArray(a.content)) { const t = a.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) a = t.text; }
      if (typeof a === 'string') { try { a = JSON.parse(a); } catch (e) { throw new Error('GitHub answered with text, not results: ' + a.slice(0, 160)); } }
      if (!a || !Array.isArray(a.items)) throw new Error('GitHub search returned no items');
      const unwrap = (x) => {
        let b = x;
        if (b && Array.isArray(b.content)) { const t = b.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) b = t.text; }
        if (typeof b === 'string') b = JSON.parse(b);
        return b;
      };
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
      return Promise.all(a.items.map(async (p) => {
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
          labels: (p.labels || []).map((l) => (typeof l === 'string' ? l : l && l.name)).filter(Boolean).join(', '),
          created_at: p.created_at, updated_at: p.updated_at, url: p.html_url,
          branch: (pr && pr.head && pr.head.ref) || '', session, run_url,
          checks: runs || status ? checksOf(runs, status) : 'Unknown', checks_url: p.html_url + '/checks',
        };
      }));
    },
  });
  dash.loader('merged_prs', {
    description: 'The GitHub search answer as one row per merged pull request',
    fn: ({ answer }) => {
      let a = answer;
      if (a && Array.isArray(a.content)) { const t = a.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) a = t.text; }
      if (typeof a === 'string') { try { a = JSON.parse(a); } catch (e) { throw new Error('GitHub answered with text, not results: ' + a.slice(0, 160)); } }
      if (!a || !Array.isArray(a.items)) throw new Error('GitHub search returned no items');
      return a.items.map((p) => ({
        repo: String(p.repository_url || '').split('/').pop(), number: p.number, title: p.title,
        author: (p.user && p.user.login) || '', closed_at: p.closed_at, url: p.html_url,
      }));
    },
  });
  dash.loader('open_issues', {
    description: 'Open issues in skills-evals, then the same call for _agent-guidance, adam-agentskills and claude-memory-map, as one row per issue',
    fn: async ({ answer, call, args }) => {
      const parse = (x) => {
        let a = x;
        if (a && Array.isArray(a.content)) { const t = a.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) a = t.text; }
        if (typeof a === 'string') { try { a = JSON.parse(a); } catch (e) { throw new Error('GitHub answered with text, not issues: ' + a.slice(0, 160)); } }
        if (!a || !Array.isArray(a.issues)) throw new Error('GitHub returned no issues list');
        return a.issues;
      };
      const sets = [[args.repo, parse(answer)]];
      for (const repo of ['_agent-guidance', 'adam-agentskills', 'claude-memory-map']) {
        sets.push([repo, parse(await call('list_issues', { ...args, repo }))]);
      }
      const rows = [];
      for (const [repo, list] of sets) for (const i of list) rows.push({
        repo, number: i.number, title: i.title,
        labels: (i.labels || []).map((l) => (typeof l === 'string' ? l : l && l.name)).filter(Boolean).join(', '),
        created_at: i.created_at, updated_at: i.updated_at,
        url: 'https://github.com/' + args.owner + '/' + repo + '/issues/' + i.number,
      });
      return rows;
    },
  });
  dash.loader('eval_ingests', {
    description: 'Commits on the results branch as rows: the run id each one saved, when, and its link',
    fn: ({ answer }) => {
      let a = answer;
      if (a && Array.isArray(a.content)) { const t = a.content.find((c) => c.type === 'text' && /^[\[{]/.test(String(c.text).trim())); if (t) a = t.text; }
      if (typeof a === 'string') { try { a = JSON.parse(a); } catch (e) { throw new Error('GitHub answered with text, not commits: ' + a.slice(0, 160)); } }
      if (!Array.isArray(a)) throw new Error('GitHub returned no commit list');
      return a.map((c) => {
        const msg = (c.commit && c.commit.message) || '';
        const m = msg.match(/routine run (\d{8}T\d{6}Z-[0-9a-f]{6})/);
        return { sha: c.sha, run_id: m ? m[1] : null, message: msg.split('\n')[0], ingested_at: c.commit && c.commit.committer && c.commit.committer.date, url: c.html_url };
      });
    },
  });
}
