# Manual Scripts

`read_manual.py` is the current single-page manual_reader utility script.
`run_manual_loop.py` is the manual-only page loop. These scripts are checkout
utilities, not part of the main `dume` CLI.

Basic command:

```bash
python scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode new-pieces
```

Manual page loop:

```bash
python scripts/manuals/run_manual_loop.py --input data/manuals/raw3
```

Keyboard confirmation is the default wait mode. Press Enter to advance, `r` to
repeat the current page, or `q` to quit.

Gesture confirmation can be enabled explicitly:

```bash
python scripts/manuals/run_manual_loop.py \
  --input data/manuals/raw3 \
  --wait-mode gesture \
  --gesture-source webcam
```

Gesture mapping:

- `THUMBS_UP` advances to the next page.
- `TWO_FINGERS` repeats the current page.
- `FIST` quits the loop as a conservative stop.
- `PALM`, `ONE_FINGER`, `THREE_FINGERS`, `NONE`, low-confidence gestures,
  unstable gestures, and cooldown-suppressed gestures do not advance the page.

Gesture mode uses the existing camera and MediaPipe gesture stack. It fails fast
if the camera, model, or MediaPipe runtime cannot start. Add
`--gesture-fallback enter` to warn and use keyboard input instead. Optional
`--gesture-timeout-s` quits for safety on timeout unless that fallback is set.

To open each generated debug preview while confirming pages:

```bash
python scripts/manuals/run_manual_loop.py \
  --input data/manuals/raw3 \
  --open-preview
```

The script prints to the terminal by default. Use `--output-dir` or
`--preview-output` when a persistent artifact is needed.

Use `--help` to inspect the full argument list when the manual-reader image
dependencies are installed.

This script-level gesture adapter is only a manual page-loop confirmation path.
It does not create LeRobot actions, call `env.step(action)`, or change dataset
schemas.

See `docs/manuals/manual_reader.md` for usage notes, visual preview options, and
current limitations.
