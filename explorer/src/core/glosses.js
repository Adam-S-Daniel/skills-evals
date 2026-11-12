/* One plain line per guidance section, keyed by the manifest id in
   _agent-guidance's agents-md/eval-coverage.yml. */

function buildGlosses(you) {
  const whose = you ? 'your' : 'the owner\'s', Whose = you ? 'Your' : 'The owner\'s';
  return {
  'working-in-these-repos': 'For any project: leave paused work alone, fix only what was asked, test every change, and use American spelling.',
  'anything-you-name-gets-its-link': 'Whenever Claude mentions something you might want to open, it gives the link right there, so you never have to go looking.',
  'finding-your-unknowns': 'Say what is unclear before starting, flag surprises while working, and write lasting lessons down where the next person will find them.',
  'turn-lessons-into-checks': 'When a mistake or a hard-won procedure could happen again, Claude records it as an automatic check, a skill or a guidance note before finishing.',
  'workstation-layout': 'Where project folders live on ' + whose + ' computers, so Claude looks in the right place.',
  'security': 'Treat anything from outside as untrusted, never mix it straight into commands, and never save passwords or keys in a project.',
  'data-exposure-in-ci': 'Logs from automated checks on public projects are visible to anyone, so personal details must never be printed there.',
  'read-before-you-start': 'A short list of reference pages to read before touching certain settings.',
  'automation-vs-branch-protection': 'The main copy of each project only accepts reviewed changes, so automated helpers must propose changes rather than write to it directly.',
  'two-github-connectors': 'Claude can reach GitHub through two different connections with different powers, and must know which one it is using.',
  'agent-contribution-markers': 'Anything Claude posts on GitHub under ' + whose + ' name ends with a note saying an AI wrote it.',
  'pr-tldr': 'Every pull request description starts with a short plain-English summary of what changes and why.',
  'github-404-means-not-authorized': 'When GitHub says "not found", it may only mean "you are not allowed to see this", so do not report something as gone on that alone.',
  'fleet-spans-two-owners': Whose + ' projects sit under two different accounts, so a search of only one gives an answer that looks complete but is wrong.',
  'watch-finished-is-not-ci-passed': 'A command that waits for the automatic checks finishing does not mean the checks passed; read the actual results.',
  'git-push-does-not-mean-commit-exists': 'Uploading changes can report success even when the new change was never saved, so confirm the change is really there.',
  'dependency-updates': 'Wait about a week before adopting a new version of an outside package, and record exact versions.',
  'name-becomes-scanner-data': 'Names that contain words like "secret" or "token" can set off the leak scanner, so choose names that describe the purpose instead.',
  'pinning-github-actions': 'Each outside building block the automation uses is locked to one exact, reviewed version, so it cannot change underneath us.',
  'test-that-can-signal-kills-every-session': 'A test once stopped every program on a computer by mistake; code that stops programs must double-check what it is about to stop.',
  'subagent-delegation': 'How Claude hands work to helper assistants, chooses cheaper models when that is safe, and checks their work before trusting it.',
  'skills-ecosystem': 'Where ' + whose + ' skills come from, how they are installed, and how a project chooses which ones to load.',
  'two-setup-gaps': 'Two one-time setup steps Claude may help with, mentioned once at most and never repeated as nagging.',
  'git-practices': 'How to save and combine changes: short, clear notes explaining why, one change at a time, and never rewriting shared history.',
  'section-docker': 'For building software containers: fixed versions, no administrator access, and no passwords inside.',
  'section-dotnet': 'For C# code: switch on the strictest warnings and keep to the version the project already uses.',
  'section-go': 'For Go code: let slow work be cancelled, run the standard checkers, and keep building blocks small.',
  'section-javascript': 'For JavaScript code: never hide errors, and stay consistent with the project\'s existing style.',
  'section-python': 'For Python code: describe what each function takes and returns, handle files carefully, and lock package versions.',
  'section-rust': 'For Rust code: explain every risky shortcut and keep crash-on-error shortcuts out of shared code.',
  'section-typescript': 'For TypeScript code: no catch-all types, and respect the project\'s strict settings.'
  };
}
export const GLOSSES = {};
export const TERMS = {};
export function useGlossVoice(v) {
  for (const k of Object.keys(GLOSSES)) delete GLOSSES[k];
  Object.assign(GLOSSES, buildGlosses(v === 'you'));
  if (typeof useTermVoice === 'function') useTermVoice(v);
}
useGlossVoice('owner');
export const GLOSS_MISSING = 'A plain-language description of this section has not been written yet.';

/* What each git hook check enforces, keyed by its id in _agent-guidance's
   templates/agent-checks/agent-checks (the refusal message is its full
   documentation). */
export const HOOK_GLOSSES = {
  'dated-phrasing': 'Warns, and never refuses, when Markdown that agents load as instructions holds dated history or phrasing relative to a migration.',
  'persistent-delete': 'Refuses a push that deletes a persistent/* branch, which outlives its pull requests and holds data such as results and usage records.',
  'pr-tldr': 'In CI, fails a pull request whose description does not open with a TLDR heading and text under it.',
  'push-to-default': 'Refuses a push straight to a default branch, which takes changes only through pull requests.',
  'rules-dir': 'Refuses path-scoped rules files (.claude/rules/), which only one tool reads; the rule belongs in AGENTS.md, a skill or a check.',
  'secret-file': 'Refuses a file that looks like a secret or credential file, because git history in a public repo is public.',
  'skill-shell': 'Refuses a skill line that would run a shell command the moment the skill loads, before anyone reads it.',
  'staged-index': 'Refuses a push while staged changes sit in no commit, so a commit a hook refused cannot slip out with the one before it.',
  'repo-local': 'Runs a repo\'s own checks (.agent-checks/local.sh) and refuses when they do.'
};

/* One definition per term the page uses, so each concept has one word and one
   meaning. `label` is the term as the page words it; `text` is what the
   definition box says. Keyed by the id `defn()` takes. */
function buildTerms(you) {
  const whose = you ? 'your' : 'the owner\'s';
  return {
  skill: { label: 'Skill', text: 'A page of instructions Claude reads before a certain kind of task. The improvement loop tests each skill and keeps, revises or removes it by the results.' },
  section: { label: 'Guidance section', text: 'One topic, under its own heading, in the guidance Claude reads at the start of every working session on ' + whose + ' projects.' },
  subject: { label: 'Subject', text: 'Whatever is being tested: a skill or a guidance section.' },
  fixture: { label: 'Fixture', text: 'One small, fixed practice task used for testing. The same task is used every time so results can be compared.' },
  arm: { label: 'Arm', text: 'One way of running a task, such as with the skill or without it. Each run compares arms.' },
  run: { label: 'Run', text: 'One test of one subject on one fixture and one model. It attempts the task several times in each arm and saves the results together.' },
  comparisonRun: { label: 'Comparison run', text: 'A run in which both arms of a comparison, such as with and without the skill, were scored together. Only these count toward a decision.' },
  trial: { label: 'Trial', text: 'A single attempt at a task by one model. A run is made of several trials.' },
  check: { label: 'Check', text: 'A yes-or-no test a computer scores without opinion, such as "did it create this file". The "checks passed" counts on this page are these.' },
  judge: { label: 'Judge', text: 'A separate AI model that reads each attempt and scores it from 0 to 10. It never takes part in the task.' },
  judgeScore: { label: 'Judge score', text: 'A grade from 0 to 10 that the judge, a separate AI model, gives after reading a transcript of the attempt. Ten is the best. It is not a pass count: the checks are scored separately.' },
  percentagePoint: { label: 'Percentage point', text: 'One point on the 0 to 100 percent scale of checks passed. Going from 75% to 25% is a drop of 50 percentage points.' },
  verdict: { label: 'Verdict', text: 'The improvement loop\'s decision about a subject: keep it, remove it, or not decided yet. The colored status label shows it.' },
  fire: { label: 'Fire', text: 'One scheduled start of a run: the loop launches a test of one subject on one model. Its results should come back to the results branch within 2 hours.' },
  sweep: { label: 'Sweep', text: 'A group of fires with no results that started within an hour of each other. A sweep usually means one outage rather than separate failures.' },
  decisive: { label: 'Decisive', text: 'A run that counted toward the point where its model-and-fixture comparison reached a keep-or-remove decision.' },
  building: { label: 'Building', text: 'A run that counts toward a model-and-fixture comparison which has not reached a decision yet.' },
  stranded: { label: 'Stranded', text: 'A usable run that a change to the text, fixture or model dropped before its comparison reached a decision.' },
  gain: { label: 'Gain', text: 'Checks passed with the subject minus checks passed without it, as a share of all checks. Plus means it helped.' },
  advantage: { label: 'Advantage', text: 'The average score with the subject minus the average score without it, on a scale from 0 to 1. Plus means it helped.' },
  trending: { label: 'Trending toward removal', text: 'Recent runs score below the runs before them, or the subject stopped beating the arm without it. This is expected and the system acts on it: if the trend holds, the loop removes the subject automatically.' },
  dataBuilt: { label: 'Results data built', text: 'When the script that turns saved runs into this page\'s data last ran, in US Eastern time. It is not when the page itself was published.' },
  newestRun: { label: 'newest run', text: 'When the most recent run recorded in the data started, in US Eastern time.' },
  blockedHooks: { label: 'Stopped', text: 'A git hook check refused a commit or push (on a local computer), or failed a pull request check in CI.' }
  };
}
export function useTermVoice(v) {
  for (const k of Object.keys(TERMS)) delete TERMS[k];
  Object.assign(TERMS, buildTerms(v === 'you'));
}
useTermVoice('owner');
