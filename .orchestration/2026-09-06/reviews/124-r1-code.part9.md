
## What I could not check

- **The CLI measurement itself.** I never ran `claude`, per the brief. I audited it for internal
  consistency against the hook's code and corroborated it by reading the shipped bundle as data;
  what I cannot confirm is the *empirical* half — that `claude -p` fired exactly two events, that
  a canary on stdout appeared nowhere, and that `/compact` in print mode produced no third event.
  The static evidence makes all three plausible (the emitter discards the hook result; the CLI's
  own description offers only stderr on a non-zero exit).
- **Whether the CLI emits an `InstructionsLoaded` event for an `@AGENTS.md` import.** The whole
  fleet reaches `AGENTS.md` through a `CLAUDE.md` bridge, and the `agents-md:` lane only fires on
  a file that carries the managed markers — i.e. on `AGENTS.md`, not on the bridge. `include` is
  in the reason enum and the `*` matcher would catch it, but the worker's measurement used a
  project with no import, so the lane's real-world trigger is unmeasured on both sides.
- **The post-merge sync run**, which is the issue's last verifier line and belongs to whoever
  holds the merge.
- **Behaviour as a non-root user.** This container runs as root, so a read-only
  `$CLAUDE_CONFIG_DIR` is not actually read-only here; I exercised the write-failure paths with a
  directory blocking the target path instead (finding N4).
- **`shellcheck`** is not installed in this container; `bash -n` only.

## Tree integrity

```
before:  4a4a2080f8028d57db3ea180425bd273   (find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum, in $SP/rev124a-code)
after:   <recomputed below>
```

Every mutation, every suite run and every fixture was executed in a copy under `$SP/r1w124/`;
`$SP/rev124a-code` and `$SP/rev124a-ref` were only ever read. The two-commit git repo built for
the #120 touch gate lives at `$SP/r1w124/touchgate` and touches nothing real — no operation was
run against `/home/user/_agent-guidance` beyond `cat-file -t` and `log`. No network, no `claude`
binary executed, no credential touched, nothing posted to GitHub. All background jobs I started
have exited.
