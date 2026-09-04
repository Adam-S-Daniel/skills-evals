# Reference pins for this fixture (resolved 2026-08-30)

This is a hermetic eval fixture: no check here resolves a SHA over the
network (see `DESIGN.md`'s note on why `pinned_shas_match_tags` retired), so
these do not need to be the real commit SHAs `actions/checkout@v4` etc.
resolve to today. Any syntactically valid 40-character hex string is accepted
— use the ones below when bringing the third-party pins in `ci.yml` into
line with the policy.

| Action | Tag | SHA |
|---|---|---|
| actions/checkout | v4 | 8c145d657eb0e222586a451c0917c3072252d69a |
| actions/setup-node | v4 | 297dbbfd3925b9ddfa3512a328e7fd3f2ca1f708 |
| actions/upload-artifact | v4.1.0 | 469fdae6c9a7a133f770f31f7ebfe863a834fba1 |
| actions/cache | v4.1.0 | 145d7281d851cb2f0e335d9b256d80c13f353f7f |

`Adam-S-Daniel/cms-platform/...@v0.1.104` refs in `deploy.yml` and
`.github/actions/gate/action.yml` are **not** third-party actions — per the
fleet carve-out (own-account `cms-platform` reusable workflows and composite
actions), they stay pinned to the release tag. Do not resolve them to a SHA.
