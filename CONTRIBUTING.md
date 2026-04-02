# Contributing to DUM-E

## Branch Structure

The project uses two development branches with a strict dependency order:

```
dev/utility  -->  dev/autonomy
     |                 |
     v                 v
          main
```

### `dev/utility` (Foundation)
Owns control, calibration, poses, motions, workspace config, manual data, and the inventory schema. Steps 1-3 of the build plan live here.

### `dev/autonomy` (Autonomy Layer)
Owns the state machine, perception integration, dock management, observability, and validation. Steps 4-12 of the build plan live here. Always builds on top of `dev/utility`.

### `main`
Receives milestone merges only after a branch passes its full checklist:
- `dev/utility` merges to `main` after Step 3 passes
- `dev/autonomy` merges to `main` after Step 11 passes

## Merge Direction Rules

1. **`dev/autonomy` rebases from `dev/utility`** -- never the reverse
2. **Never merge `dev/autonomy` into `dev/utility`** -- the utility layer must stay independent of autonomy code
3. If autonomy work reveals that a pose, config, or utility contract needs to change, make that change on `dev/utility` first, then rebase `dev/autonomy` to pick it up
4. Do not push directly to `main` -- all changes flow through the development branches

## Branch Switch Point

After Step 3 is complete and checked on `dev/utility`, rebase `dev/autonomy` from `dev/utility` to pick up all foundation work. From that point forward, all new code goes on `dev/autonomy`.

## Pull Request Guidelines

- PR target branch must match the step being implemented (see build plan)
- Steps 1-3: target `dev/utility`
- Steps 4-12: target `dev/autonomy`
- Milestone merges to `main`: require all checklist items for the phase to pass
- Keep PRs focused on a single step when possible
