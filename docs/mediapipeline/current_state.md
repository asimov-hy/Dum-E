# DUM-E MediaPipeline Current State

Last updated: 2026-05-11.

## Phase Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0 | Automated PASS | Shared contracts and import-boundary tests pass. |
| Phase 1 | Automated PASS | Fake/webcam/RealSense-lazy source tests pass without hardware. |
| Phase 2 | Automated PASS | MediaPipe VIDEO-mode service, canned mapper, and drop-NONE tests pass. |
| Phase 3 | Automated PASS | Finger-state geometry and full mapper tests pass. Manual webcam checks were not recorded. |
| Phase 4 | Automated PASS | Confidence, drop-NONE, stability, cooldown, and operator-stub tests pass. Manual webcam checks were not recorded. |
| Phase 5 | Infrastructure PARTIAL PASS | Video source, model checksum workflow, regression manifest, and regression harness exist. Recorded clips are missing. |

Known automated result before this recording-scaffold update:

```text
full suite: 149 passed, 19 skipped
regression media: 1 passed, 19 skipped
```

Latest scaffold validation result after adding the camera-specific suite
placeholders:

```text
full suite: 159 passed, 21 skipped
regression media: 1 passed, 21 skipped
```

The skipped regression-media cases are skipped because clips are missing or
marked `present=false` in `data/mediapipe/regression_media/manifest.json`.

## Current Paths

- MediaPipe model checksum:
  `data/mediapipe/models/gesture_recognizer.task.sha256`
- Local MediaPipe model artifact:
  `data/mediapipe/models/gesture_recognizer.task`
- Regression media manifest:
  `data/mediapipe/regression_media/manifest.json`
- MediaPipe scripts: `scripts/mediapipe/`
- MediaPipeline docs: `docs/mediapipeline/`
- LeRobot camera adapter placeholder:
  `src/dume/integrations/lerobot/camera_adapter.py`

Legacy path note: prefer `docs/mediapipeline/phase_verification_checklist.md`
for the checklist. `docs/mediapipeline_phase_verification_checklist.md` is a
tracked compatibility pointer.

## Manual Validation

- Live webcam validation has not been recorded.
- Live RealSense validation has not been recorded.
- Phase 3 gesture checks remain outstanding.
- Manual Phase 4 filter/stability/cooldown checks remain outstanding.

The user has observed that webcam labels gestures correctly while RealSense may
fail. Treat webcam and RealSense RGB behavior as separate compatibility surfaces
until recorded evidence says otherwise.

## Phase 5 Policy

- Phase 5 full PASS requires one complete required `primary` regression suite.
- Missing `primary` clips with `required_for_phase5=true` keep Phase 5 at
  PARTIAL PASS.
- `webcam` and `realsense_rgb` suites are optional compatibility suites unless a
  clip is explicitly marked `required_for_acceptance=true`.
- Optional missing camera-specific clips do not block ordinary unit tests.
- Strict checks fail when required clips are missing:

```bash
python scripts/mediapipe/check_regression_media.py --strict
DUME_REQUIRE_REGRESSION_MEDIA=1 python -m pytest -q tests/test_regression_media.py
```

This strict failure is expected while required primary clips are missing. Do not
add fake media or mark missing clips present to silence it.

## Deferred Due To Camera Access

- Capture primary recorded regression suite.
- Capture webcam compatibility clips.
- Capture RealSense RGB compatibility clips.
- Compare webcam and RealSense raw labels, mapped gestures, and filter behavior.
- Record RealSense color-order, resolution, exposure/lighting, and failure
  cases.
- Run final manual demo checks for Phase 3 and Phase 4.

Phase 5 cannot be marked PASS until required recorded media exists and
regression tests execute against it instead of skipping.
