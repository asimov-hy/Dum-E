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
- `docs/manuals/README.md`: future manual-reading notes.
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
