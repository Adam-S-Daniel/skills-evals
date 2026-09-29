# The usage census

`scripts/model_usage_census.py` counts which Claude models this account
actually ran, per ISO week, from the local Claude Code transcripts under
`~/.claude/projects`. `scripts/publish_usage_census.sh` runs it and publishes
the result as `usage/latest.json` on the `eval-results` branch. `harness/roster.py`
reads that file to decide which models earn an arm's seat; when it is absent or
older than 14 days the roster falls back to "newest model per tier" and says so
in every arm's reason ("no fresh census"). Nothing fails silently — but nothing
refreshes the census either, until somebody schedules it.

## Why it runs on the owner's durable machine

It reads transcripts, and only the machine where Claude Code is used day to day
has them. A GitHub runner has none, and a cloud session has only its own. So
this is neither a workflow nor a Routine: it is a scheduled task on the owner's
own machine, which is why the owner sets it up himself (below).

It used to ride along as a step of the Tier-3 account-store Routine. That
Routine, and the audit it existed for, were retired on 2026-09-28 (see
`HANDOFF.md`, the 2026-09-28 amendment near the top), so the census needed its own home.

## The privacy contract

The output is committed to a **public** branch, so it is the narrowest thing
that answers the question: `{model_id: {iso_week: count}}`, plus the metadata
keys `generated_at` and `weeks`. No project names, no paths, no prompt or reply
text, no session ids, no timestamp finer than a week. The transcripts carry every
one of those; `~/.claude/projects/` encodes the project path in the directory
name alone.

- Weekly buckets, not daily: a daily series over one account is a record of when
  a person was at their desk, and the roster policy only asks about 4- and
  8-week windows.
- Keys are not trusted either. `message.model` is whatever the routing layer
  wrote, and has been observed carrying a Bedrock ARN (an AWS account number), a
  Vertex path (a GCP project id) and free prose. Only values shaped like a model
  id become keys; everything else is counted under the single key `other`.
- The guard is a test, not a convention:
  `test/run_tests.py::TestIssue67::test_census_emits_only_model_week_counts_and_leaks_nothing`
  (and its `TestIssue67Review` siblings) runs the parser over a transcript
  carrying a project path and prose and asserts neither survives into the output.
  `TestPublishUsageCensus` runs the same shape end to end through the publish
  script against a local bare repository and asserts the pushed file holds only
  those keys and that the script's one summary line holds totals only.
- The publish script prints one line — model count, turn total, week count — with
  no path under `$HOME` and no per-model figures. It handles no token: it uses
  the git credentials the machine already has.

## Setting it up (the owner does this once)

Prerequisites on the machine: `git` with push access to
`Adam-S-Daniel/skills-evals` over HTTPS or SSH (the credentials you already use),
`python3`, and PyYAML (`python3 -m pip install --user pyyaml`; the census reads
the tier ladder from `evals/roster-policy.yml` through `harness/roster.py`).

Try it first. A dry run does everything except the push:

```bash
bash /path/to/skills-evals/scripts/publish_usage_census.sh --dry-run
```

It prints e.g. `usage census: 4 models, 1234 assistant turns, 8 weeks; dry run,
committed locally and pushed nothing`. The script clones skills-evals into a temp
dir itself, so it always runs the census from `main`, and it re-publishes at least
every 6 days even when the counts have not moved, so an idle account does not age
out of the roster's 14-day freshness window.

### Option A: a Claude Desktop scheduled task

Create a scheduled task, daily, with this prompt (replace the path with where
your checkout of skills-evals lives on that machine):

```text
Run exactly this command and report its single output line, or its error if it
fails. Do not edit any file, do not run anything else, and do not print the
contents of any Claude Code transcript.

bash ~/repos/Adam-S-Daniel/skills-evals/scripts/publish_usage_census.sh
```

### Option B: cron (or a systemd timer) in WSL

Daily at 06:37 local time, with the output kept in a log you can read:

```cron
37 6 * * * bash "$HOME/repos/Adam-S-Daniel/skills-evals/scripts/publish_usage_census.sh" >> "$HOME/.cache/usage-census.log" 2>&1
```

Add it with `crontab -e`. WSL only runs cron while a WSL instance is running and
the `cron` service is started, so a laptop that sleeps will skip days; the
14-day freshness window tolerates that. A systemd user timer that runs the same
`bash …/publish_usage_census.sh` line is equivalent.

### Checking that it works

`git ls-remote https://github.com/Adam-S-Daniel/skills-evals eval-results` should
move after a run that found changed counts, and the branch's
`usage/latest.json` carries the run's `generated_at`. The next roster run
(`roster/latest.json`) reports the census timestamp in its `source.census_at`.
