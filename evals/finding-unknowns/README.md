# Finding unknowns fixture

This Class C fixture covers the pre-implementation pass in
[issue #78](https://github.com/Adam-S-Daniel/skills-evals/issues/78). The seed
contains a working CSV helper, a failing empty-export acceptance test, an
accepted bounded-export decision, and an old route whose compatibility is an
open product question. The request does not identify those sources or supply
the two operator answers.

Three objective checks only certify that the reply cites the relevant file
paths. The fourth checks that source files were left unchanged. Those checks
cannot establish that the agent read or understood the files, or that it asked
useful questions. The blind pairwise judge carries those judgments, using two
hand-written references outside `seed/` and anchored score levels in the
fixture rubric. A path-only or semantically wrong reply can pass the lexical
checks and should score poorly with the judge. Source edits fail the separate
objective check; the pairwise judge does not receive workspace diffs or check
results and cannot rank on unseen edits.

The references are not copied into the agent workspace. Pairwise rank is
noisy; any later balanced comparison needs at least six trials per arm, a
multiple of six for the three-draft permutation cycle. The schema and scorer
support pairwise ranking, but [`harness/run_eval.py`](../../harness/run_eval.py)
currently rejects a judged pairwise run before either arm with
`judge_mode_unsupported` (exit 2). Its comment attributes the missing runner
wiring to [issue #97](https://github.com/Adam-S-Daniel/skills-evals/issues/97),
which is closed; the implementation gap remains. This package does not claim
a measured A/B improvement or cover the skill's during-build notes and
post-build explanation steps.
