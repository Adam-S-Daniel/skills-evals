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

### The seed pre-pass: provenance, not markup

Every check here sets `strip_seed: true`, so it is scored over the reply
with the **seed's own material** removed (`objective.strip_seed_material`),
and the greeting and the hedge over only its opening. Without it a reply
that pasted the cold email back was scored on the recruiter's words — her
"I think your background lines up well" satisfied the hedge check, and her
signature satisfied the greeting.

Two earlier attempts decided that from **markup**, and both failed, in
opposite directions. A line scanner (`^ {0,3}>` plus a fence tracker)
cannot see an indented code block, an HTML `<blockquote>`/`<details>`/
`<pre>`, a lazy continuation, or a verbatim paste carrying no marker at
all; a real Markdown parser sees every one of those and still cannot tell
a quoted seed from a deliverable the agent *chose* to present as a
blockquote — which is exactly what every calibration example in SKILL.md
is, so the `with_skill` arm is the one most likely to hand its reply back
in that shape.

What separates the two is not markup. It is **provenance**: `seed/` is
committed material this harness reads, so the material that came from it
can be named in any shape it is pasted back in, and everything else is the
agent's writing however it chose to format it.

**The unit of provenance is the sentence**, and the decision is taken
*after* hard wrapping is undone. It used to be the line, and a line is not
a unit of anything: the same words re-broken across different lines are a
different set of lines, so a paste re-wrapped, re-selected onto one line,
punctuated with a trailing `!`, run through a Markdown table or salted
with one invisible character per line walked straight past the scan — and
in the other direction a genuine third-person bio hard-wrapped at 72 lost
two of *its own* lines, because a wrap landed where the background note's
line ends do.

In order:

1. **Invisibles fold out** — zero-width characters, soft hyphens,
   variation selectors, the Mongolian vowel separator and the rest.
2. **Wrapper comes off, and only wrapper**: leading whitespace, `>` runs
   with any number of spaces after them, list markers, fence delimiters, a
   table's alignment row, and the bare tags `blockquote`, `details`,
   `summary`, `pre`, `code`, `div`, `p`, `br` when they carry **no
   attributes**. Everything else is the agent's text and stays exactly as
   it arrived — an HTML comment, a tag outside that set, a tag with
   attributes, and its attribute values with it.
3. **Hard wrapping is undone**, paragraph by paragraph, by the same
   `harness/scorers/wrapping.py` helpers the judge normalises drafts with,
   so the judge and the objective column cannot read one draft two ways.
4. **Each line splits into sentences** at `.`, `!`, `?` and `;` followed by
   whitespace, and at the line break that ends a list item or a table row.
5. **A sentence is the seed's** when its word key — casefolded,
   punctuation dropped, whitespace collapsed — is a contiguous run of some
   seed file's own text and at least 24 characters, or *is* one of the
   seed's sentences whole and at least 12 (an exact sentence match is
   stronger evidence than a substring, so it earns the lower floor). A
   maximal run of consecutive sentences that are all the seed's goes whole
   when the run carries at least one piece above the floor: that is what a
   paste is, and the short pieces inside it came with it. Inside a
   **marked** quotation — a fence, an HTML wrapper, a `>` run — there is no
   floor at all, because the markup has already said the block is a
   quotation.
6. **The residue is what is left**, and both `must_match` and
   `must_not_match` are scored over it. A reply that is nothing but the
   material has an empty residue and fails its `must_match` checks — the
   right answer for a reply that wrote nothing — while a reply the agent
   merely wrapped in `> ` stays, unwrapped, and its bans fire.

**It is opt-in, per check.** A global pre-pass narrowed an unrelated
shipped fixture: `windows-elevation-from-wsl` asks the reply to hand over a
command, the command is in the seed, and stripping it left the handoff
check failing a transcript that put it in a ```powershell fence. Only these
three fixtures set `strip_seed`, and it has to be a real boolean — a
`strip_seed: "no"` read by truthiness turned the pre-pass *on*.

**What it does not do**, stated because all three limits are real:

- A fact the agent restates in **its own sentence** is its own writing and
  is scored, even though the fact is in the seed. "REQ-4417 is not going to
  work for me" counts; the recruiter's sentence carrying REQ-4417 does not.
  That is the point, not a leak. By the same rule a sentence the agent
  **composed** out of the seed's phrases — two seed runs joined by its own
  connective, a seed clause inside its own sentence — carries a word order
  the seed does not have and stays.
- A sentence that reproduces the seed's own words **end to end** is the
  seed's even where the skill told the agent to write exactly that: core
  move 8's plain certifications listing has one natural phrasing, and the
  background note carries it. It costs no check — nothing a check looks for
  is only in a line the agent could have copied — and the judge reads the
  draft, not the residue.
- Anything **shorter than the floors** is the agent's, so an *unmarked*
  paste can leave a bare name behind when nothing around it is long enough
  to anchor the run. The floors are what keep the agent's own "Thanks," and
  its own sign-off from being claimed by the seed.

The known failure mode in the other direction stays, and each fixture's
header records it: commentary the agent wraps *around* the writing really
is the agent's writing, so it is scored as if it were the writing. "I kept
it free of 'leverage'" fails the avoid-list check — directional against the
`with_skill` arm, since the arm that knows the list is the arm that
mentions it — and in the bio a "That is the paragraph he asked for."
satisfies `bio-is-third-person` on the commentary's own pronoun. That is
why every brief asks for the text alone, nothing before or after it and
nothing quoted.

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
