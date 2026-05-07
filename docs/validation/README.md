# DUM-E Validation Guide

This is the validation command index. It points to the canonical details instead
of replacing them.

## Document Ownership

- `README.md`: concise human-facing overview and basic setup.
- `docs/TECHNICAL.md`: canonical agent/developer RAG guide.
- `docs/validation/README.md`: validation command index.
- `docs/mediapipeline_current_state.md`: current MediaPipeline status.
- `docs/mediapipeline_recording_plan.md`: how to record required clips.
- `docs/mediapipeline_phase_verification_checklist.md`: phase checklist.
- `data/test_media/README.md`: test-media directory instructions.

## General Validation

Run inside the intended active environment:

```bash
python -m pytest -q
python -m ruff check src tests core camera perception demos scripts
git diff --check
```

See `docs/TECHNICAL.md` for environment policy, dependency policy, and
architecture boundaries.

## MediaPipeline Validation

```bash
python scripts/download_gesture_model.py
python -m pytest -q tests/test_regression_media.py
python scripts/check_regression_media.py
python scripts/check_regression_media.py --strict
```

Strict media validation is expected to fail while required primary clips are
missing. That failure keeps Phase 5 at PARTIAL PASS and must not be hidden with
fake media or changed manifest truth.

The gesture model binary is a local/external artifact. Track
`data/models/gesture_recognizer.task.sha256` and use
`python scripts/download_gesture_model.py` to recreate or verify
`data/models/gesture_recognizer.task`.

Current status:

- `docs/mediapipeline_current_state.md`
- `data/test_media/manifest.json`

Capture plan:

- `docs/mediapipeline_recording_plan.md`

Phase checklist:

- `docs/mediapipeline_phase_verification_checklist.md`

## Diagnostic Scripts

`scripts/diagnose_gesture_channel_order.py` is diagnostic only. Use it when a
camera appears to detect hands but MediaPipe canned labels differ between raw
OpenCV BGR input and BGR-to-RGB converted input. It compares `AS_IS` and
`BGR2RGB` paths directly against MediaPipe output and is not part of normal
validation.
