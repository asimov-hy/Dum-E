# DUM-E MediaPipeline Recording Plan

## Purpose

Recorded regression clips make the gesture prototype reproducible without a live
camera. They let us compare raw labels, geometry, filtering, latency, misses, and
false positives across camera backends.

Canonical media root: `data/mediapipe/regression_media/`.

Keep MediaPipe regression media separate from:
- manual/reference inputs under `data/manuals/`
- future LeRobot datasets or episodes under `data/lerobot/`

## Suites

- `primary`: required for Phase 5 full PASS. This suite should be recorded in a
  stable baseline setup and must cover all target and rejection cases.
- `webcam`: optional compatibility suite for webcam behavior.
- `realsense_rgb`: optional compatibility suite for RealSense RGB behavior.
- `custom`: optional stress or edge-case clips. Promote a clip by setting
  `required_for_acceptance=true` in the manifest.

Because webcam and RealSense behavior may differ, RealSense RGB clips are kept
separate from webcam clips. Missing optional camera-specific clips do not block
ordinary unit tests.

## Minimum Primary Clips

Record these before Phase 5 can be marked PASS:

- Clear thumbs up.
- Clear fist.
- Clear palm.
- Index only.
- Index + middle.
- Index + middle + ring.
- Middle only.
- Ring only.
- Thumb + index.
- Four fingers with thumb folded.
- No hand.
- Partial hand entering frame.
- Partial hand leaving frame.
- Poor lighting.
- Motion blur or rapid movement.
- Two hands visible.
- Thumbs up from side angle.
- Three-finger ring-finger stress case.
- Raw-label oscillation sequence such as `Victory` / `None` / `Victory`.

Recommended duration: 3 to 8 seconds per clip.

## Framing

- Keep the hand fully visible for baseline target clips.
- Use the same hand orientation expected in demo use.
- Do not mirror or flip frames before recording or inference.
- Use stable lighting for baseline clips.
- Record stress conditions separately from baseline clips.
- Record handedness, approximate distance to camera, background, lighting, FPS,
  and resolution in the manifest or sidecar metadata.

## RealSense RGB Notes

- Capture the RGB stream, not a depth visualization.
- Verify that `Frame.rgb` is RGB internally.
- Record camera model, serial if available, resolution, FPS, exposure/lighting,
  and distance to camera.
- Document RealSense failures separately from webcam failures.
- Do not promote RealSense clips to acceptance-blocking until the team agrees on
  expected RealSense behavior.

## Recording Procedure

Example webcam recording:

```bash
python scripts/mediapipe/record_regression_clip.py \
  --source webcam \
  --output data/mediapipe/regression_media/webcam/thumbs_up_clear.mp4 \
  --clip-id webcam_thumbs_up_clear \
  --expected THUMBS_UP \
  --suite webcam \
  --camera-backend webcam \
  --camera-model "laptop webcam" \
  --resolution 640x480 \
  --fps 30 \
  --duration-seconds 5 \
  --notes "clear thumbs up"
```

Example RealSense RGB recording:

```bash
python scripts/mediapipe/record_regression_clip.py \
  --source realsense \
  --output data/mediapipe/regression_media/realsense_rgb/thumbs_up_clear.mp4 \
  --clip-id realsense_rgb_thumbs_up_clear \
  --expected THUMBS_UP \
  --suite realsense_rgb \
  --camera-backend realsense \
  --camera-model "Intel RealSense D435" \
  --resolution 640x480 \
  --fps 30 \
  --duration-seconds 5 \
  --notes "RGB stream, stable lighting"
```

The recording script writes a sidecar JSON next to the clip and prints a
suggested manifest entry. It does not edit `manifest.json` automatically.

## Manifest Update Procedure

1. Place the clip under `data/mediapipe/regression_media/<suite>/`.
2. Review the sidecar JSON written by `scripts/mediapipe/record_regression_clip.py`.
3. Add or update the manifest entry.
4. Set `present=true` only after the file exists and is readable.
5. Use `required_for_phase5=true` only for primary clips needed for Phase 5 PASS.
6. Use `required_for_acceptance=true` for optional camera-specific clips only
   when they must block final acceptance.
7. Do not add fake media or mark missing clips present.

## Status Checks

Run:

```bash
python scripts/mediapipe/check_regression_media.py
python scripts/mediapipe/check_regression_media.py --suite webcam
python scripts/mediapipe/check_regression_media.py --suite realsense_rgb
python scripts/mediapipe/check_regression_media.py --strict
```

Strict mode is expected to fail until required primary clips are present.

## Regression Tests

Default local/CI run:

```bash
python -m pytest -q tests/test_regression_media.py
```

Strict required-media mode:

```bash
DUME_REQUIRE_REGRESSION_MEDIA=1 python -m pytest -q tests/test_regression_media.py
```

Skipped media means the harness is working but Phase 5 remains PARTIAL PASS.
Skipped camera-specific compatibility clips do not block ordinary unit tests
unless they are marked required.
