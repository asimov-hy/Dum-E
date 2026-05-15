# Manual Scripts

`read_manual.py` is the current single-page manual_reader utility script.
`run_manual_loop.py` is the manual-only page loop. These scripts are checkout
utilities, not part of the main `dume` CLI.

Basic command:

```bash
python scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode new-pieces
```

Root launcher manual page loop:

```bash
python main.py
python main.py check
python main.py setup
python main.py --config configs/manual_loop.local.yaml check
```

The root launcher reads `configs/manual_loop.default.yaml`, then either
`configs/manual_loop.local.yaml` or an explicit `--config` file, then CLI
overrides. `configs/manual_loop.local.yaml` is gitignored for machine-local
camera/model choices. The default config uses `manual.wait_mode: enter`, so it
is keyboard-only and does not start camera, MediaPipe, RealSense, LeRobot, or
robot-control dependencies.

Gesture sources are `fake`, `webcam`, `realsense`, and `video`. Use
`--gesture-device` for a webcam index and `--gesture-video-path` for video
files. Gesture mapping accepts enum names such as `THUMBS_UP` or lowercase names
such as `thumbs_up`, with actions restricted to `advance`, `repeat`, `quit`,
and `none`. `none` means no page-loop action. Keyboard fallback and timeout are
configured with `fallback: enter` / `--gesture-fallback enter` and
`timeout_s` / `--gesture-timeout-s`.

This launcher and the script below are manual-page confirmation only. They do
not add LeRobot teleoperation, call `env.step(action)`, or change action tensors
or dataset schemas.

Script-level manual page loop:

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
