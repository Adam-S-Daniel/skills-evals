<!-- fictional -->

# `adam-writing-style` — three Class C fixtures

The Class C pilot from [#81]. Class C means the judge carries the load: the
few decidable bits are scored objectively, and the comparison is a **pairwise
preference against committed reference samples** rather than an absolute
rubric score (DESIGN.md, "Four instruments, one harness"). DESIGN.md's
warning applies — expect noise, and run **N >= 6 trials per arm, and a
multiple of 6**: the shuffle walks a cycle of n! = 6 permutations (the draft
under test plus two references), so a trial count that is not a whole number
of cycles leaves slot balance to whichever part of the cycle the run
happened to cover. N = 5 gives one slot twice, another twice and the third
once, which is position bias bought back by accident.

| Fixture | Register | Prompt |
|---|---|---|
| `recruiter-reply/` | email | Reply to this recruiter's cold email in my voice, declining but leaving the door open |
| `proposal-bio/` | third person | Write my 60-word bio for this proposal |
| `self-appraisal-opening/` | first person | Draft the opening paragraph of my self-appraisal for this quarter from these notes. |

Three registers, three small fixtures: the proposal bio and the
self-appraisal are opposite halves of the skill (core moves 8 and 9), and a
single merged fixture would hide an arm that got one right and the other
wrong.

## Running them

Each directory is a complete eval dir on its own — `fixture.yaml`, `seed/`,
`references/` — because the multi-fixture runner ([#66]) has not landed.

> [!WARNING]
> **`run_eval.py` does not honour `judge.mode` yet.** The runner still calls
> `judge.score()` with the arguments it knew before [#81], so each
> fixture's `judge:` block reaches it without its `mode:` or its
> `references:`. Running these fixtures used to hand them to the ABSOLUTE
> judge against a *ranking* rubric, silently: measured on
> `recruiter-reply`, exit 0 and a report reading `Judge overall | 7.5`,
> which is not a rank and means nothing here. The runner now **refuses**
> instead — a fixture whose `judge.mode` is not `absolute` exits 2 with a
> named `judge_mode_unsupported` error in `report.md` and `summary.json`,
> before any arm runs — so pass `--no-judge` and treat the objective column
> as the only score this runner produces.
> `harness/scorers/judge.py` is complete and tested end to end
> (`judge.score_fixture`); it is the call site that has not moved, and
> moving it is [#97]'s change, not this fixture set's.
>
> [#97] has a second, older gap to pick up while it is in there:
> `run_agent` passes the prompt in **argv** with no `OSError` catch, so a
> missing or unexecutable CLI is an uncaught traceback with no `report.md`
> and no `summary.json` — the judge call fixed exactly this for itself
> (stdin, and every `OSError` translated) and the agent call never
> followed.

That means three invocations by hand:

```sh
# --no-judge until run_eval.py honours judge.mode: see the warning above.
for f in recruiter-reply proposal-bio self-appraisal-opening; do
  python3 harness/run_eval.py evals/adam-writing-style/$f --arm both \
    --registry agentskills=../agentskills --no-judge
done
```

`--arm objective-only` on a pristine seed **exits 1**, with every check
reporting "no transcript". That is the documented asymmetry, not a broken
fixture: every check here is `transcript_matches` — the writing IS the
transcript — and objective-only mode runs no agent, so there is nothing to
match against.

## What is objective, and what is not

Objective (`transcript_matches` only): none of the skill's avoid-list words
survive; the recipient is greeted by name and the reply opens with a hedge;
the bio is third person and the self-appraisal first person; both facts the
seed material carries are cited.

The two facts per fixture sit in the *material* — the recruiter's own email,
a background note, the quarter's notes — and no brief asks for them to be
quoted. A brief that said "cite these" would score instruction-following,
which both arms pass, instead of the skill's specificity move, which is the
thing under test.

Everything else — the sixty-word budget, whether the em dashes land at the
right joints, whether the warmth is real — is the judge's.

Every check reads the agent's reply with the material it **quoted**
removed, and the greeting and the hedge only its opening: a reply that
quotes the cold email back was otherwise scored on the recruiter's words —
her "I think your background lines up well" satisfied the hedge check, and
her signature satisfied the greeting.

The stripping is one pre-pass (`objective.strip_quoted`), not an anchor per
pattern. The anchor it replaced (`(?m)^(?!>)`, written out 47 times) only
ever saw a line whose *first* character is `>`, so a fenced code block and
a blockquote indented one to three spaces — legal Markdown, and what a
model actually writes — walked past all 47. A reply quoted in its
**entirety** is scored whole: otherwise a draft could switch the avoid-list
ban off by wrapping itself in `> `, and every calibration example in
SKILL.md is a `>` blockquote, so the with-skill arm is the one most likely
to mirror the shape.

The known failure mode in the other direction stays, and each fixture's
header records it: commentary the agent wraps *around* the writing is
scored as if it were the writing, so "I kept it free of 'leverage'" fails
the avoid-list check. It is directional against the `with_skill` arm — the
arm that knows the list is the arm that mentions it — which is why every
brief now asks for the text alone, nothing before or after it and nothing
quoted.

## The references

Two per fixture, in `references/`: one in the voice, one competent but
generic. They are **written text, not generated**, and Adam should read them
as prose before this lands — they are the yardstick every future run of this
eval is measured against.

All six contract (`I'm`, `isn't`, `he's`), because the skill's own register
does and this fixture's hedge regex accepts `I'm guessing`. The first drafts
of them did not — nought apostrophes across all six — which cost twice: a
model's reply with a single contraction was separable from every reference
on every trial, and the register the judge ranked against was a
de-contracted version of the voice under test.

They deliberately live beside `fixture.yaml` rather than inside `seed/`:
`seed/` is copied into the agent's workspace, so a reference in there would
hand the agent the answer and flatten both arms.

The judge sees them blind and it sees them *level*: every draft is unwrapped
to the same line shape before the prompt is built (these references are
hard-wrapped prose and a model's reply is not, which would otherwise mark
the odd draft out on every trial), each is fenced with a per-call nonce so
nothing inside a draft can pose as the prompt, and the `<!-- fictional -->`
line each reference opens with is stripped — from the candidate as well as
from the references, so an agent that echoed the line is not marked out by
it either.

## Fiction

Every person, employer, client, RFP and requisition number in these fixtures
is invented, and the only addresses are `example.com` / `example.net`. This
repository is public and fixtures are committed.

The `<!-- fictional -->` marker opens every `.md` outside a `seed/` — the
six references and this README — and appears in **no** file under any
`seed/`. `seed/` is copied into the agent's workspace, so a marker there
tells the agent under test that its own brief is invented, and makes the
one candidate that mirrors the line the one draft the judge can pick out of
a blind set. Each seed's fiction is recorded instead at the top of its
`fixture.yaml`, which sits beside `seed/` and is never copied into the
workspace.

[#81]: https://github.com/Adam-S-Daniel/skills-evals/issues/81
[#66]: https://github.com/Adam-S-Daniel/skills-evals/issues/66
[#97]: https://github.com/Adam-S-Daniel/skills-evals/issues/97
