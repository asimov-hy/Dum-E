# DUM-E Validation Guide

This is the validation command index. It points to the canonical details instead
of replacing them.

## Document Ownership

- `README.md`: concise human-facing overview and basic setup.
- `docs/TECHNICAL.md`: canonical agent/developer RAG guide.
- `docs/validation/README.md`: validation command index.
- `docs/mediapipeline/current_state.md`: current MediaPipeline status.
- `docs/mediapipeline/recording_plan.md`: how to record required clips.
- `docs/mediapipeline/phase_verification_checklist.md`: phase checklist.
- `docs/manuals/README.md`: current manual_reader lane index.
- `docs/mediapipe/README.md`: MediaPipe-specific notes outside the phase docs.
- `docs/lerobot/README.md`: future LeRobot integration notes.
- `data/mediapipe/regression_media/README.md`: regression-media directory instructions.

## General Validation

Run inside the intended active environment:

```bash
python -m pytest -q
python -m ruff check .
git diff --check
```

See `docs/TECHNICAL.md` for environment policy, dependency policy, and
architecture boundaries.

## MediaPipeline Validation

```bash
python scripts/mediapipe/download_gesture_model.py
python -m pytest -q tests/test_regression_media.py
python scripts/mediapipe/check_regression_media.py
python scripts/mediapipe/check_regression_media.py --strict
```

Strict media validation is expected to fail while required primary clips are
missing. That failure keeps Phase 5 at PARTIAL PASS and must not be hidden with
fake media or changed manifest truth.

`python scripts/mediapipe/check_regression_media.py` should pass in non-strict
mode while reporting missing clips.
`python scripts/mediapipe/check_regression_media.py --strict` is expected to
fail until the required clips are recorded. `tests/test_regression_media.py` may
skip missing clips unless strict environment flags require them.

The gesture model binary is a local/external artifact. Track
`data/mediapipe/models/gesture_recognizer.task.sha256` and use
`python scripts/mediapipe/download_gesture_model.py` to recreate or verify
`data/mediapipe/models/gesture_recognizer.task`.

Current status:

- `docs/mediapipeline/current_state.md`
- `data/mediapipe/regression_media/manifest.json`

Capture plan:

- `docs/mediapipeline/recording_plan.md`

Phase checklist:

- `docs/mediapipeline/phase_verification_checklist.md`

## Manual Reader Validation

Official validation should run in the conda `dume` environment. Alternate
Python environments or temporary dependency installs can help during local
debugging, but they are not official validation.

```bash
python -m pytest -q tests/test_manual_reader.py tests/test_manual_color_detector.py
python -m ruff check .
python scripts/manuals/read_manual.py --help
```

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces
```

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces \
  --debug-components \
  --preview-output /tmp/manual_debug.png
```

The reader is Prototype-Partial. Current smoke expectations are C1 JPEG green
only, and C3 JPEG green plus red while rejecting pale/light-blue old blocks.
Passing these checks does not solve clean PNG/manual accuracy: those images can
still over-count studs, faces, or components. Treat current counts as
best-effort diagnostics. Clean PNG accuracy is not accepted yet until component
grouping and color-set output are fixed.

## Diagnostic Scripts

`scripts/mediapipe/diagnose_gesture_channel_order.py` is diagnostic only. Use it when a
camera appears to detect hands but MediaPipe canned labels differ between raw
OpenCV BGR input and BGR-to-RGB converted input. It compares `AS_IS` and
`BGR2RGB` paths directly against MediaPipe output and is not part of normal
validation.

## Organization Checks

Use these scans after moving docs, assets, or scripts:

```bash
rg -n "data/models|data/test_media|docs/mediapipeline_|scripts/check_regression_media|scripts/download_gesture_model|scripts/record_regression_clip|camera/lerobot_adapter" README.md docs data scripts tests src core camera perception demos pyproject.toml .gitignore
git status --short --branch --untracked-files=all
```

Expected current locations:

- MediaPipe model/checksum: `data/mediapipe/models/`
- Regression media manifest: `data/mediapipe/regression_media/manifest.json`
- MediaPipe scripts: `scripts/mediapipe/`
- MediaPipeline docs: `docs/mediapipeline/`
- LeRobot integration placeholder:
  `src/dume/integrations/lerobot/camera_adapter.py`
