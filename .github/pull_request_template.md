## What does this change?

<!-- One or two sentences. Link an issue if there is one. -->

## Why?

<!-- What problem does this solve, or what gap does it close? -->

## Testing

<!-- What did you actually run, and what happened? Be specific — "tests pass"
     is not enough if you changed behavior; show the command and outcome. -->

- [ ] `cargo test --release --all-features` passes
- [ ] `pytest tests/ -v` passes
- [ ] New behavior has a new test (not just "existing tests still pass")

## Honesty check

- [ ] If this changes what the library does or doesn't do, `README.md`'s
      "Honest feature list" / "What's not here" sections are updated to match
- [ ] No new placeholder/stub code that looks like it works but doesn't
      (see `ROADMAP_HONEST.md` for what "doesn't work" already looks like here)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
