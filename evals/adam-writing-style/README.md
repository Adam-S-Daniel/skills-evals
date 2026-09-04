# `adam-writing-style` — three Class C fixtures

The Class C pilot from [#81]. Class C means the judge carries the load: the
few decidable bits are scored objectively, and the comparison is a **pairwise
preference against committed reference samples** rather than an absolute
rubric score (DESIGN.md, "Four instruments, one harness"). DESIGN.md's
warning applies — expect noise, and run **N ≥ 5 trials per arm**.

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
That means three invocations by hand:

```sh
for f in recruiter-reply proposal-bio self-appraisal-opening; do
  python3 harness/run_eval.py evals/adam-writing-style/$f --arm both \
    --registry agentskills=../agentskills
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

## The references

Two per fixture, in `references/`: one in the voice, one competent but
generic. They are **written text, not generated**, and Adam should read them
as prose before this lands — they are the yardstick every future run of this
eval is measured against.

They deliberately live beside `fixture.yaml` rather than inside `seed/`:
`seed/` is copied into the agent's workspace, so a reference in there would
hand the agent the answer and flatten both arms.

## Fiction

Every person, employer, client, RFP and requisition number in these fixtures
is invented, and the only addresses are `example.com` / `example.net`. This
repository is public and fixtures are committed.

[#81]: https://github.com/Adam-S-Daniel/skills-evals/issues/81
[#66]: https://github.com/Adam-S-Daniel/skills-evals/issues/66
