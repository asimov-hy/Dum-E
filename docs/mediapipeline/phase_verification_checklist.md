# DUM-E MediaPipeline Phase Verification Checklist

Use this checklist after each implementation phase. Do not begin the next phase until the current phase gate passes.

Canonical plan reference: `docs/mediapipeline_build_plan_v5.md` or equivalent.

## How to use this checklist

For each phase:

1. Run the automated checks.
2. Complete the manual checks where hardware or live MediaPipe behavior is involved.
3. Record failures, fixes, and unresolved risks.
4. Mark the phase gate as PASS only when all required checks pass.

Recommended run log:

```text
Phase:
Date:
Branch / commit:
Environment:
Python version:
OS:
Camera hardware, if used:
MediaPipe model path, if used:
Result: PASS / FAIL
Notes:
```

## Global checks after every phase

These checks should remain true throughout the project.

### Architecture and import boundaries

- [ ] `core/` does not import from `camera/`.
- [ ] `core/` does not import from `perception/`.
- [ ] `camera/` may import from `core/`, but not from `perception/`.
- [ ] `perception/` may import from `core/`, but not from `camera/`.
- [ ] `demos/` may import from `core/`, `camera/`, and `perception/`.
- [ ] Robot command/autonomy code is not added inside `perception/`.
- [ ] `Frame` remains in `core/frame.py`, not `camera/`.
- [ ] `GestureService` consumes `Frame` or frame-derived core data, not camera backend objects.
- [ ] `GestureObservation` is used for debug/overlay data and may include `NONE`.
- [ ] `GestureEvent` is command-relevant and never has `type=GestureType.NONE`.

### Runtime and testing discipline

- [ ] No phase implements future-phase behavior unless explicitly listed as a stub.
- [ ] Unit tests for the current and previous phases still pass.
- [ ] Manual hardware checks are documented when run.
- [ ] Optional backends fail gracefully if dependencies are missing.
- [ ] No runtime network download is required for normal execution.
- [ ] Debug logs are sufficient to distinguish camera, MediaPipe, geometry, mapping, and filtering failures.

Recommended global command:

```bash
python -m pytest -q
```

Use this only once the relevant tests exist. Earlier phases should run the phase-specific subset below.

---

# Phase 0 — Package skeleton and shared contracts

## Purpose

Establish shared data contracts and import boundaries before camera, MediaPipe, or OpenCV code exists.

## Expected files

- [ ] `core/frame.py`
- [ ] `core/types.py`
- [ ] `core/landmarks.py`
- [ ] `camera/__init__.py`
- [ ] `perception/__init__.py`
- [ ] `perception/types.py`
- [ ] `tests/test_core_contracts.py`
- [ ] `tests/test_import_boundaries.py`

## Automated checks

Run:

```bash
python -m pytest -q tests/test_core_contracts.py tests/test_import_boundaries.py
```

### Core contract checks

- [ ] `Frame` exists in `core/frame.py`.
- [ ] `Frame.rgb` is documented as RGB, `uint8`, HWC, C-contiguous.
- [ ] `Frame.timestamp_ms` is documented as monotonic and strictly increasing.
- [ ] `Frame.frame_id` exists and is optional.
- [ ] `Frame.depth_m` exists and is optional.
- [ ] `Frame.camera_name` exists and is optional.
- [ ] `validate_frame()` accepts valid RGB `uint8` HWC contiguous frames.
- [ ] `validate_frame()` rejects wrong ndim.
- [ ] `validate_frame()` rejects wrong channel count.
- [ ] `validate_frame()` rejects non-`uint8` arrays.
- [ ] `validate_frame()` rejects non-contiguous arrays.
- [ ] `Landmark2D` exists in `core/landmarks.py`.
- [ ] `Landmark3D` exists in `core/landmarks.py`.
- [ ] `FrameSource` protocol exists in `core/types.py` with `start()`, `stop()`, and `get_frame()`.

### Perception type checks

- [ ] `GestureType` contains exactly the six target gestures plus `NONE`.
- [ ] `GestureType.NONE` is documented as rejection-only.
- [ ] `GestureSource` contains `CANNED`, `GEOMETRY`, and `HYBRID`.
- [ ] `MappedGesture` contains `type`, `confidence`, and `source`.
- [ ] `FingerState` contains `thumb`, `index`, `middle`, `ring`, and `pinky` booleans.
- [ ] `FingerStateResult` contains `state`, optional `confidence`, and optional `margins`.
- [ ] `GestureObservation` contains landmarks fields and optional finger-state fields.
- [ ] `GestureEvent` does not claim to carry `NONE` events.
- [ ] `OperatorPresence` contains `present`, `confidence`, and optional `bbox_xyxy`.
- [ ] `GestureServiceConfig` includes `max_num_hands=1` by default.
- [ ] `GestureServiceConfig` includes `min_hand_detection_confidence`.
- [ ] `GestureServiceConfig` includes `min_hand_presence_confidence`.
- [ ] `GestureServiceConfig` includes `min_tracking_confidence`.

### Import-boundary checks

- [ ] Importing `core` does not import `camera`.
- [ ] Importing `core` does not import `perception`.
- [ ] Importing `camera` does not import `perception`.
- [ ] Importing `perception` does not import `camera`.
- [ ] Phase 0 test environment does not require MediaPipe.
- [ ] Phase 0 test environment does not require OpenCV.
- [ ] Phase 0 test environment does not require RealSense.
- [ ] Phase 0 test environment does not require LeRobot.

## Manual checks

- [ ] Inspect package layout and confirm no camera or MediaPipe implementation has been added yet.
- [ ] Confirm `NONE` is described as a rejection class, not one of the six target gestures.
- [ ] Confirm documentation says accuracy is measured over the six target gestures and rejection behavior is measured separately.

## Red flags

Do not proceed if any of these are true:

- [ ] `Frame` lives in `camera/`.
- [ ] `perception/` imports from `camera/`.
- [ ] `camera/` imports from `perception/`.
- [ ] `GestureEvent` is allowed to emit `NONE`.
- [ ] Phase 0 requires MediaPipe or OpenCV to run tests.

## Phase gate

Phase 0 passes when:

- [ ] All Phase 0 automated tests pass.
- [ ] Import boundaries are verified.
- [ ] No external runtime dependencies are required.
- [ ] All shared data contracts are present and documented.

Result: `PASS / FAIL`

---

# Phase 1 — Camera sources

## Purpose

Produce valid RGB `Frame` objects from at least one source, with reliable timestamps, frame IDs, and cleanup.

## Expected files

- [ ] `camera/opencv_backend.py`
- [ ] `camera/realsense_backend.py` if RealSense is supported, with lazy import
- [ ] `camera/lerobot_adapter.py` if LeRobot integration is supported
- [ ] `camera/source.py`
- [ ] `demos/camera_smoke.py`
- [ ] `tests/test_camera_fake_source.py`

## Automated checks

Run:

```bash
python -m pytest -q \
  tests/test_core_contracts.py \
  tests/test_import_boundaries.py \
  tests/test_camera_fake_source.py
```

### FakeSource checks

- [ ] FakeSource can be constructed without camera hardware.
- [ ] FakeSource implements `FrameSource`.
- [ ] FakeSource yields valid `Frame` objects.
- [ ] `validate_frame(frame)` passes for FakeSource frames.
- [ ] `timestamp_ms` increases strictly across emitted frames.
- [ ] `frame_id` increases strictly across emitted frames when present.
- [ ] FakeSource supports `start()` and `stop()`.
- [ ] FakeSource supports context-manager usage, if implemented.

### Backend import checks

- [ ] Importing webcam backend does not require RealSense.
- [ ] Importing `camera/source.py` does not require RealSense.
- [ ] RealSense dependency is imported lazily inside `start()` or equivalent, not at module import time.
- [ ] Camera package still does not import `perception/`.
- [ ] MediaPipe is not required for Phase 1 tests.

## Manual webcam check

Run:

```bash
python demos/camera_smoke.py --source webcam --frames 100
```

Verify:

- [ ] Script captures 100 frames.
- [ ] FPS is printed.
- [ ] Actual resolution is printed.
- [ ] If actual resolution differs from requested resolution, a warning is logged and the script continues.
- [ ] Frame display works.
- [ ] Display conversion is RGB to BGR at the display boundary only.
- [ ] `frame.rgb.ndim == 3`.
- [ ] `frame.rgb.shape[2] == 3`.
- [ ] `frame.rgb.dtype == np.uint8`.
- [ ] `frame.rgb.flags["C_CONTIGUOUS"]` is true.
- [ ] `timestamp_ms` is strictly increasing.
- [ ] `frame_id` is strictly increasing when present.
- [ ] `camera_name` is populated or intentionally documented as `None`.
- [ ] Device is released on normal exit.
- [ ] Device is released on Ctrl+C or exception path.
- [ ] Device is released after context-manager exit.

## Optional RealSense check

Run only if RealSense hardware is available:

```bash
python demos/camera_smoke.py --source realsense --frames 100
```

Verify:

- [ ] Script captures 100 frames.
- [ ] RGB frames pass `validate_frame()`.
- [ ] `depth_m` is present.
- [ ] `depth_m` has shape `(H, W)` matching the RGB frame resolution, or mismatch is documented.
- [ ] `depth_m` is in meters.
- [ ] Device cleanup works.
- [ ] Webcam-only users do not see RealSense import errors.

## Optional LeRobot adapter check

Run only if integrating with LeRobot:

- [ ] Adapter wraps existing LeRobot camera classes rather than duplicating connection/cleanup logic.
- [ ] Adapter implements `FrameSource`.
- [ ] Adapter emits `Frame` with RGB internal convention.
- [ ] Adapter preserves or creates monotonic timestamps.
- [ ] Adapter cleanup delegates to LeRobot camera cleanup.

## Debug information to record

```text
Backend:
Requested resolution:
Actual resolution:
Average FPS:
Min / max frame interval:
Timestamp source:
Frame ID behavior:
Cleanup verified: yes/no
```

## Red flags

Do not proceed if any of these are true:

- [ ] Frames are BGR internally.
- [ ] RGB/BGR conversion happens repeatedly outside camera/display boundaries.
- [ ] Timestamps can repeat or go backward.
- [ ] Camera resources stay locked after script exit.
- [ ] Webcam backend imports RealSense at module import time.
- [ ] Camera package imports perception.

## Phase gate

Phase 1 passes when:

- [ ] Phase 0 checks still pass.
- [ ] FakeSource tests pass.
- [ ] At least one real or simulated camera source produces valid frames.
- [ ] Timestamps and frame IDs are monotonic.
- [ ] Cleanup is verified.
- [ ] MediaPipe is still not required.

Result: `PASS / FAIL`

---

# Phase 2 — MediaPipe canned semantic gestures

## Purpose

Integrate MediaPipe Gesture Recognizer in synchronous `VIDEO` mode and recognize three canned semantic targets: `THUMBS_UP`, `PALM`, and `FIST`.

## Expected files

- [ ] `perception/gesture.py`
- [ ] `perception/mapper.py`
- [ ] `perception/filters.py` with `DropNoneFilter` only or minimal chain
- [ ] `demos/gesture_demo.py`, Phase 2 version
- [ ] `tests/test_gesture_service_timestamp.py`
- [ ] `tests/test_canned_mapper.py`
- [ ] `tests/test_drop_none_filter.py`
- [ ] `tests/test_overlay_no_finger_state.py`
- [ ] `scripts/download_gesture_model.py`
- [ ] `data/models/gesture_recognizer.task`, or documented local model path
- [ ] `data/models/gesture_recognizer.task.sha256`, if using checksum file

## Automated checks

Run:

```bash
python -m pytest -q \
  tests/test_core_contracts.py \
  tests/test_import_boundaries.py \
  tests/test_gesture_service_timestamp.py \
  tests/test_canned_mapper.py \
  tests/test_drop_none_filter.py \
  tests/test_overlay_no_finger_state.py
```

### Model checks

- [ ] Model path is configurable.
- [ ] GestureService validates that model path exists.
- [ ] Missing model raises a clear error with download instructions.
- [ ] Model is not downloaded at runtime by `GestureService`.
- [ ] Download script exists if model is not committed.
- [ ] SHA-256 verification exists or is documented.

### MediaPipe mode checks

- [ ] Gesture Recognizer uses `VisionRunningMode.VIDEO`.
- [ ] GestureService uses `recognize_for_video(...)`.
- [ ] GestureService does not wrap `LIVE_STREAM` callbacks.
- [ ] `max_num_hands` defaults to `1`.
- [ ] `min_hand_detection_confidence` is passed to MediaPipe options.
- [ ] `min_hand_presence_confidence` is passed to MediaPipe options.
- [ ] `min_tracking_confidence` is passed to MediaPipe options.

### GestureService API checks

- [ ] `analyze_frame(frame)` exists and runs inference.
- [ ] `events_from_observations(frame, observations)` exists and does not run inference.
- [ ] `process_frame(frame)` exists as analyze + filter convenience.
- [ ] Calling `analyze_frame(frame)` and then `events_from_observations(frame, observations)` does not trigger duplicate inference.
- [ ] Calling `process_frame(frame)` after `analyze_frame(frame)` on the same timestamp raises due to timestamp guard, or is explicitly documented as invalid.
- [ ] Timestamp guard rejects duplicate timestamps.
- [ ] Timestamp guard rejects decreasing timestamps.
- [ ] Timestamp guard accepts strictly increasing timestamps.
- [ ] `close()` closes the MediaPipe recognizer.

### Phase 2 mapper checks

- [ ] `Thumb_Up` maps to `THUMBS_UP` with `source=CANNED`.
- [ ] `Open_Palm` maps to `PALM` with `source=CANNED`.
- [ ] `Closed_Fist` maps to `FIST` with `source=CANNED`.
- [ ] `Victory` maps to `NONE` in Phase 2.
- [ ] `Pointing_Up` maps to `NONE` in Phase 2.
- [ ] `Thumb_Down` maps to `NONE`.
- [ ] Unknown labels map to `NONE`.
- [ ] `None` raw label maps to `NONE`.
- [ ] `NONE` observations are dropped from event output.

### Observation checks

- [ ] `GestureObservation` includes raw label and raw confidence.
- [ ] `GestureObservation` includes handedness when available.
- [ ] `GestureObservation` includes hand index.
- [ ] `GestureObservation` includes `Landmark2D` landmarks when MediaPipe returns them.
- [ ] `GestureObservation` includes `Landmark3D` world landmarks when MediaPipe returns them.
- [ ] `finger_state` is `None` in Phase 2.
- [ ] `finger_state_result` is `None` in Phase 2.
- [ ] `finger_count` is `None` in Phase 2.
- [ ] Overlay can draw landmarks without finger-state data.
- [ ] Overlay does not assume landmarks and finger state are present together.

## Manual live checks

Run:

```bash
python demos/gesture_demo.py --source webcam --draw-landmarks --log-observations --log-events
```

Verify:

- [ ] No hand produces empty observations or no command events.
- [ ] Thumbs up produces `GestureObservation(type=THUMBS_UP, source=CANNED)`.
- [ ] Thumbs up produces a `GestureEvent(type=THUMBS_UP)`.
- [ ] Open palm produces `GestureObservation(type=PALM, source=CANNED)`.
- [ ] Open palm produces a `GestureEvent(type=PALM)`.
- [ ] Closed fist produces `GestureObservation(type=FIST, source=CANNED)`.
- [ ] Closed fist produces a `GestureEvent(type=FIST)`.
- [ ] Thumb down produces `GestureObservation(type=NONE)` or equivalent debug output.
- [ ] Thumb down does not produce a `GestureEvent`.
- [ ] Landmarks are drawn even though finger state is unavailable.
- [ ] Finger-state overlay is hidden or displays `not available`.
- [ ] Per-frame latency is printed.
- [ ] Runtime is stable for at least 100 frames.

## Debug information to record

```text
Model path:
Model checksum verified: yes/no
Average latency ms:
Raw labels observed:
Event labels emitted:
Dropped NONE labels observed:
Timestamp guard tested: yes/no
```

## Red flags

Do not proceed if any of these are true:

- [ ] GestureService uses `LIVE_STREAM` for the synchronous API.
- [ ] `Closed_Fist` is not mapped to `FIST`.
- [ ] `NONE` can become a `GestureEvent`.
- [ ] Overlay crashes when `finger_state_result is None`.
- [ ] MediaPipe model downloads at runtime.
- [ ] Duplicate timestamps are accepted silently.
- [ ] Perception imports camera internals.

## Phase gate

Phase 2 passes when:

- [ ] Phase 0 and Phase 1 checks still pass.
- [ ] Canned semantic gestures work: `THUMBS_UP`, `PALM`, `FIST`.
- [ ] `NONE` is observable for debug but not emitted as a command event.
- [ ] Landmarks are available for overlay.
- [ ] Finger state is not required yet.
- [ ] Timestamp guard is verified.

Result: `PASS / FAIL`

---

# Phase 3 — Finger-state geometry and full mapper

## Purpose

Compute which fingers are extended from landmarks, map canonical numeric gestures, and combine geometry with canned labels without making geometry a fallback-only path.

## Expected files

- [ ] `perception/finger_state.py`
- [ ] Updated `perception/mapper.py`
- [ ] Updated `perception/gesture.py`
- [ ] `tests/test_finger_state_detector.py`
- [ ] `tests/test_gesture_mapper_geometry.py`
- [ ] `tests/test_gesture_mapper_collisions.py`

## Automated checks

Run:

```bash
python -m pytest -q \
  tests/test_core_contracts.py \
  tests/test_import_boundaries.py \
  tests/test_finger_state_detector.py \
  tests/test_gesture_mapper_geometry.py \
  tests/test_gesture_mapper_collisions.py \
  tests/test_canned_mapper.py
```

### FingerStateDetector checks

- [ ] Detector accepts `tuple[Landmark2D, ...]`.
- [ ] Detector accepts optional `tuple[Landmark3D, ...]` but does not require it for v1 classification.
- [ ] Detector accepts handedness.
- [ ] Detector returns `FingerStateResult`.
- [ ] `FingerStateResult.state` contains five booleans.
- [ ] `FingerStateResult.margins` is populated or intentionally `None` with documentation.
- [ ] `FingerStateResult.confidence` is populated or intentionally `None` with documentation.
- [ ] v1 uses image landmarks for tip-vs-PIP logic.
- [ ] world landmarks are stored/available for v2 but not treated as a drop-in replacement for image y-comparison.
- [ ] Index extended check uses fingertip vs PIP y-coordinate.
- [ ] Middle extended check uses fingertip vs PIP y-coordinate.
- [ ] Ring extended check uses fingertip vs PIP y-coordinate.
- [ ] Pinky extended check uses fingertip vs PIP y-coordinate.
- [ ] Thumb check accounts for handedness.
- [ ] Frames are not flipped before inference.

### Synthetic landmark checks

- [ ] Thumb only produces `thumb=True`, others false.
- [ ] Closed fist produces all false.
- [ ] Open palm produces all or expected fingers true.
- [ ] Index only produces index true only.
- [ ] Index + middle produces index and middle true only.
- [ ] Index + middle + ring produces index, middle, and ring true only.
- [ ] Middle only produces middle true only.
- [ ] Ring only produces ring true only.
- [ ] Thumb + index produces thumb and index true.
- [ ] Four fingers with thumb folded produces index, middle, ring, pinky true and thumb false.

### Mapper checks

- [ ] Mapper accepts `raw_label`, `raw_confidence`, and optional `FingerStateResult`.
- [ ] Mapper returns `MappedGesture`, not a bare `GestureType`.
- [ ] Geometry confidence comes from `FingerStateResult.confidence` or explicit config default.
- [ ] No hidden hard-coded geometry confidence exists outside config.
- [ ] `HYBRID` is returned when canned semantic label and compatible geometry agree.
- [ ] `CANNED` is returned when canned semantic label is accepted but geometry is absent or incompatible.
- [ ] `GEOMETRY` is returned when geometry alone decides.

### Mandatory collision tests

- [ ] `raw_label=Thumb_Up`, finger state thumb only -> `THUMBS_UP`, `HYBRID`.
- [ ] `raw_label=Thumb_Up`, bad geometry -> `THUMBS_UP`, `CANNED`.
- [ ] `raw_label=Closed_Fist`, all fingers false -> `FIST`, `HYBRID`.
- [ ] `raw_label=Closed_Fist`, bad geometry -> `FIST`, `CANNED`.
- [ ] `raw_label=Open_Palm`, all/four fingers open -> `PALM`, `HYBRID` or documented source behavior.
- [ ] `raw_label=Open_Palm`, bad geometry -> `PALM`, `CANNED`.
- [ ] `raw_label=Pointing_Up`, index only -> `ONE_FINGER`, `GEOMETRY`.
- [ ] `raw_label=Victory`, index + middle -> `TWO_FINGERS`, `GEOMETRY`.
- [ ] `raw_label=None`, index + middle + ring -> `THREE_FINGERS`, `GEOMETRY`.
- [ ] `raw_label=None`, middle only -> `NONE`.
- [ ] `raw_label=None`, ring only -> `NONE`.
- [ ] `raw_label=None`, index + middle + ring + pinky -> `PALM`, `GEOMETRY`, if `allow_geometry_palm=True`.
- [ ] `raw_label=Thumb_Down`, thumb only -> `NONE`.
- [ ] `raw_label=None`, thumb + index -> `NONE`.

### GestureService wiring checks

- [ ] `FingerStateDetector` is wired only in Phase 3 or later.
- [ ] For every detected hand with landmarks, finger state is computed.
- [ ] Finger state is not gated on `raw_label is None`.
- [ ] Canned label and geometry are computed in parallel.
- [ ] Observations carry raw label, mapped type, source, finger state, finger count, and landmarks.
- [ ] `Pointing_Up` and `Victory` are preserved as `raw_label` metadata and do not override geometry.

## Manual live checks

Run:

```bash
python demos/gesture_demo.py \
  --source webcam \
  --draw-landmarks \
  --draw-finger-state \
  --log-observations
```

Verify:

- [ ] Index only -> `ONE_FINGER`.
- [ ] Index + middle -> `TWO_FINGERS`.
- [ ] Index + middle + ring -> `THREE_FINGERS`.
- [ ] Thumbs up -> `THUMBS_UP`, not `ONE_FINGER`.
- [ ] Open palm -> `PALM`.
- [ ] Closed fist -> `FIST`.
- [ ] Middle finger only -> `NONE`.
- [ ] Ring finger only -> `NONE`.
- [ ] Four fingers with thumb folded -> `PALM` if geometry fallback is enabled.
- [ ] Thumb + index -> `NONE`.
- [ ] Peace sign maps to `TWO_FINGERS`, even if raw label is `Victory`.
- [ ] Pointing-up/index-only maps to `ONE_FINGER`, even if raw label is `Pointing_Up`.
- [ ] Raw label and mapped type are both visible in logs.
- [ ] Finger-state booleans are visible in logs or overlay.
- [ ] Per-finger margins are visible when available.

## Stress and limitation checks

- [ ] Hold three fingers for at least 5 seconds and record whether ring finger oscillates.
- [ ] Tilt hand about 30 degrees and record failure mode.
- [ ] Test left-hand thumb behavior.
- [ ] Test right-hand thumb behavior.
- [ ] Confirm display flipping is not applied before inference.
- [ ] Document any handedness/thumb-direction issues.

## Debug information to record

```text
Pose:
Raw label:
Raw confidence:
Mapped type:
Mapped confidence:
Source: CANNED / GEOMETRY / HYBRID
Finger state: thumb/index/middle/ring/pinky
Finger count:
Margins:
Handedness:
Frame ID:
Timestamp:
```

## Red flags

Do not proceed if any of these are true:

- [ ] Finger state runs only when raw label is missing.
- [ ] Middle finger only maps to `ONE_FINGER`.
- [ ] Thumb + index maps to `ONE_FINGER`.
- [ ] Thumbs up maps to `ONE_FINGER`.
- [ ] `Victory` directly maps to `TWO_FINGERS` without geometry.
- [ ] `Pointing_Up` directly maps to `ONE_FINGER` without geometry.
- [ ] Mapper returns bare `GestureType` instead of `MappedGesture`.
- [ ] Canned and geometry source are not visible in logs.

## Phase gate

Phase 3 passes when:

- [ ] Phase 0 through Phase 2 checks still pass.
- [ ] All six target gestures work before temporal filters.
- [ ] `NONE` rejection works for unsupported poses.
- [ ] Canned-label collisions are handled correctly.
- [ ] Finger-state debug output is sufficient to diagnose failures.

Result: `PASS / FAIL`

---

# Phase 4 — Full filter chain and operator stub

## Purpose

Suppress accidental triggers, require stable deliberate gestures, prevent duplicate events, and add a separate operator-presence stub.

## Expected files

- [ ] Updated `perception/filters.py`
- [ ] `perception/operator.py`
- [ ] `tests/test_filters_confidence.py`
- [ ] `tests/test_filters_drop_none.py`
- [ ] `tests/test_filters_stability.py`
- [ ] `tests/test_filters_cooldown.py`
- [ ] `tests/test_filters_frame_boundary.py`
- [ ] `tests/test_operator_mock.py`

## Automated checks

Run:

```bash
python -m pytest -q \
  tests/test_filters_confidence.py \
  tests/test_filters_drop_none.py \
  tests/test_filters_stability.py \
  tests/test_filters_cooldown.py \
  tests/test_filters_frame_boundary.py \
  tests/test_operator_mock.py
```

Then run the full current suite:

```bash
python -m pytest -q
```

### Filter-chain checks

- [ ] Filter order is confidence -> drop NONE -> stability -> cooldown.
- [ ] `FilterChain.apply()` receives observations and the current `Frame`.
- [ ] One `FilterChain.apply()` call represents exactly one frame.
- [ ] Observations are not accumulated across frames before filtering.
- [ ] `FilterChain.apply()` rejects observations with mismatched `timestamp_ms`.
- [ ] `FilterChain.apply()` rejects observations with mismatched `camera_name`.
- [ ] `FilterChain.apply()` rejects observations with mismatched `frame_id`, or documents the exact optional-None policy.
- [ ] Empty observations are valid and reset stability streaks.

### ConfidenceFilter checks

- [ ] Observations below `min_confidence` are dropped.
- [ ] Observations equal to threshold are handled according to documented policy.
- [ ] Dropped observations do not advance stability.
- [ ] Confidence filter is testable without camera or MediaPipe.

### DropNoneFilter checks

- [ ] `GestureType.NONE` observations are dropped.
- [ ] `GestureType.NONE` never becomes a `GestureEvent`.
- [ ] Stable high-confidence unsupported gestures, such as `Thumb_Down`, emit no events.
- [ ] Dropped `NONE` observations do not advance stability.

### StabilityFilter checks

- [ ] Stability key is `(type, handedness, camera_name)`.
- [ ] Stability key does not include `raw_label`.
- [ ] Stability key does not include `finger_count`.
- [ ] Stability requires exactly `N` consecutive matching frames.
- [ ] Event is emitted on the Nth stable frame.
- [ ] No event is emitted before N frames.
- [ ] Hand disappearance resets active streaks.
- [ ] Empty observation frame resets active streaks.
- [ ] Confidence-filtered candidate resets or fails to advance the streak according to documented behavior.
- [ ] A missing frame is treated as a break, not a pause.
- [ ] Raw-label flicker does not break stability if mapped type remains stable.

### CooldownFilter checks

- [ ] Cooldown uses `frame.timestamp_ms` or event timestamp, not wall-clock time.
- [ ] Same key is suppressed within cooldown window.
- [ ] Same key is allowed again after cooldown expires.
- [ ] Different keys cool down independently.
- [ ] Tests are deterministic for recorded-video timestamps.

### Mandatory synthetic sequences

- [ ] `THUMBS_UP`, `THUMBS_UP`, `THUMBS_UP` -> one event on frame 3 when `stability_frames=3`.
- [ ] `THUMBS_UP` held for 10 frames -> no duplicate during cooldown.
- [ ] `TWO_FINGERS`, `TWO_FINGERS`, no hand, `TWO_FINGERS` -> no event because streak resets.
- [ ] Raw-label flicker `Victory` / `None` / `Victory` with mapped `TWO_FINGERS` -> stabilizes.
- [ ] `Thumb_Down` mapped to `NONE` for 10 frames -> no event.
- [ ] Low-confidence `PALM` for 10 frames -> no event.
- [ ] `PALM` then `FIST` -> independent keys.
- [ ] Mismatched observation timestamp -> `ValueError`.
- [ ] Mismatched camera name -> `ValueError`.
- [ ] Empty observations reset stability.

### Operator stub checks

- [ ] `OperatorDetector` protocol exists.
- [ ] `MockOperatorDetector.detect(frame)` returns `OperatorPresence(present=True)`.
- [ ] `OperatorPresence.confidence` defaults to `1.0`.
- [ ] `OperatorPresence.bbox_xyxy` can be `None`.
- [ ] Operator detection is not embedded inside `GestureService`.
- [ ] Future command layer can check operator presence separately from gesture events.

## Manual live checks

Run:

```bash
python demos/gesture_demo.py \
  --source webcam \
  --draw-landmarks \
  --draw-finger-state \
  --draw-filter-state \
  --log-events
```

Verify:

- [ ] Casual hand movement produces no spurious command events.
- [ ] Deliberate thumbs up fires after the stability window.
- [ ] Deliberate palm fires after the stability window.
- [ ] Deliberate fist fires after the stability window.
- [ ] Deliberate one-finger gesture fires after the stability window.
- [ ] Deliberate two-finger gesture fires after the stability window.
- [ ] Deliberate three-finger gesture fires after the stability window, allowing for known ring-finger limitations.
- [ ] Holding a gesture does not spam duplicate events during cooldown.
- [ ] Switching to a different gesture produces a new event after stability.
- [ ] Removing the hand resets the streak.
- [ ] Reintroducing the same hand after removal starts a fresh streak.
- [ ] Filter debug output shows confidence pass/drop, NONE drop, stability count, cooldown pass/drop, and emitted events.

## Debug information to record

```text
Filter config:
Stability frame count:
Cooldown seconds:
Event timestamps:
Dropped low-confidence count:
Dropped NONE count:
Stability counts per key:
Cooldown suppressions:
```

## Red flags

Do not proceed if any of these are true:

- [ ] `NONE` can be emitted as a command event.
- [ ] Stability key includes `raw_label`.
- [ ] Stability does not reset when hand disappears.
- [ ] Cooldown uses `time.time()` instead of frame/event timestamp.
- [ ] Same gesture repeats continuously while held.
- [ ] Operator presence is mixed into GestureService.
- [ ] Filters require camera or MediaPipe to test.

## Phase gate

Phase 4 passes when:

- [ ] Phase 0 through Phase 3 checks still pass.
- [ ] All filter unit tests pass.
- [ ] Live demo is stable and non-spammy.
- [ ] Operator stub is separate and testable.
- [ ] Filter debug output is sufficient to diagnose suppressed or emitted events.

Result: `PASS / FAIL`

---

# Phase 5 — Demo, recording, regression suite, and packaging

## Purpose

Make the prototype reproducible without a live camera and prepare the project for repeatable development.

## Expected files

- [ ] Final `demos/gesture_demo.py`
- [ ] `scripts/download_gesture_model.py`
- [ ] `tests/test_regression_media.py`
- [ ] `data/test_media/` or documented external media path
- [ ] `data/models/gesture_recognizer.task` or documented model artifact path
- [ ] `data/models/gesture_recognizer.task.sha256`
- [ ] Updated `pyproject.toml`
- [ ] README or docs entry for setup and model download

## Automated checks

Run:

```bash
python -m pytest -q
```

If regression media is separate or slow, run:

```bash
python -m pytest -q tests/test_regression_media.py
```

### Demo checks

- [ ] `demos/gesture_demo.py` supports `--source webcam`.
- [ ] `demos/gesture_demo.py` supports `--source realsense` if RealSense backend exists.
- [ ] `demos/gesture_demo.py` supports `--source video:<path>` or documented video source option.
- [ ] Demo supports `--show-flipped-display` or equivalent display-only flip option.
- [ ] Demo supports `--log-observations`.
- [ ] Demo supports `--log-events`.
- [ ] Demo supports `--draw-landmarks`.
- [ ] Demo supports `--draw-finger-state`.
- [ ] Demo supports `--draw-filter-state`.
- [ ] Demo loop calls `analyze_frame(frame)` once per frame.
- [ ] Demo loop then calls `events_from_observations(frame, observations)`.
- [ ] Demo does not call `process_frame(frame)` after `analyze_frame(frame)` on the same frame.
- [ ] Demo exits cleanly on `q`.
- [ ] Demo exits cleanly on Ctrl+C.
- [ ] Camera and recognizer resources are closed on exit.

### Regression media coverage

Record or provide clips for:

- [ ] Clear thumbs up.
- [ ] Clear fist.
- [ ] Clear palm.
- [ ] Index only.
- [ ] Index + middle.
- [ ] Index + middle + ring.
- [ ] Middle only.
- [ ] Ring only.
- [ ] Thumb + index.
- [ ] Four fingers with thumb folded.
- [ ] No hand.
- [ ] Partial hand entering frame.
- [ ] Partial hand leaving frame.
- [ ] Poor lighting.
- [ ] Motion blur or rapid movement.
- [ ] Two hands visible, with `max_num_hands=1` behavior documented.
- [ ] Thumbs up from side angle.
- [ ] Three-finger ring-finger stress case.
- [ ] Raw-label oscillation sequence, such as `Victory` / `None` / `Victory`.

### Regression test checks

- [ ] Tests can run without a physical camera.
- [ ] Tests can run on recorded media or image sequences.
- [ ] Each clip declares expected target or expected `NONE` rejection.
- [ ] Results report observed events.
- [ ] Results report first detection timestamp.
- [ ] Results report misses.
- [ ] Results report false positives.
- [ ] Results report raw-label distribution.
- [ ] Results report source distribution: `CANNED`, `GEOMETRY`, `HYBRID`.
- [ ] Accuracy is reported over six target gestures.
- [ ] `NONE` rejection behavior is reported separately.
- [ ] Latency per frame is reported.
- [ ] Time-to-event after stability filter is reported in frames and milliseconds.

### Packaging checks

- [ ] `pyproject.toml` includes optional dependency group for camera usage.
- [ ] `pyproject.toml` includes optional dependency group for perception usage.
- [ ] `pyproject.toml` includes optional dependency group for RealSense usage, if supported.
- [ ] `pyproject.toml` includes dev/test dependencies.
- [ ] Developers can run Phase 0 tests without MediaPipe.
- [ ] Developers can run camera-only tests without MediaPipe.
- [ ] Developers can import webcam code without RealSense installed.
- [ ] Model path is documented.
- [ ] Model download script verifies SHA-256.
- [ ] Runtime code does not download the model automatically.

## Manual final demo check

Run:

```bash
python demos/gesture_demo.py \
  --source webcam \
  --log-observations \
  --log-events \
  --draw-landmarks \
  --draw-finger-state \
  --draw-filter-state
```

Verify all target classes:

- [ ] `THUMBS_UP` emits correctly.
- [ ] `FIST` emits correctly.
- [ ] `PALM` emits correctly.
- [ ] `ONE_FINGER` emits correctly for index only.
- [ ] `TWO_FINGERS` emits correctly for index + middle.
- [ ] `THREE_FINGERS` emits correctly for index + middle + ring.
- [ ] `NONE` rejection works for middle only.
- [ ] `NONE` rejection works for ring only.
- [ ] `NONE` rejection works for thumb + index.
- [ ] `NONE` rejection works for no hand.
- [ ] `Thumb_Down` does not emit a command event.
- [ ] Four fingers with thumb folded maps according to config, normally `PALM`.
- [ ] Held gestures do not spam events.
- [ ] Casual movement does not trigger events.

## Metrics to record

```text
Per-class accuracy over six target gestures:
  THUMBS_UP:
  FIST:
  PALM:
  ONE_FINGER:
  TWO_FINGERS:
  THREE_FINGERS:
NONE rejection false-positive rate:
Average latency per frame:
P95 latency per frame:
Average time-to-event:
Missed detection cases:
Common false positives:
Most common raw labels:
Source distribution:
```

## Red flags

Do not mark Phase 5 complete if any of these are true:

- [ ] No recorded regression media exists.
- [ ] Tests require a live camera.
- [ ] Accuracy and `NONE` rejection are mixed into one metric.
- [ ] Runtime downloads the model.
- [ ] Demo double-runs inference on the same frame.
- [ ] Demo flips frames before inference.
- [ ] Demo does not close camera/recognizer resources on exit.
- [ ] Unsupported poses frequently emit command events.

## Phase gate

Phase 5 passes when:

- [ ] Full automated test suite passes.
- [ ] Recorded-media regression tests run against required primary clips and
      pass within accepted thresholds. Documented failures keep Phase 5 at FAIL
      or PARTIAL PASS.
- [ ] Final demo works with overlays, logs, and clean shutdown.
- [ ] Packaging and dependency extras are correct.
- [ ] Model download/setup is reproducible.
- [ ] Metrics are reported separately for six target gestures and `NONE` rejection.

Result: `PASS / FAIL`

---

# Final acceptance checklist

Use this after all phases are complete.

## Architecture

- [ ] `core/`, `camera/`, and `perception/` remain separated.
- [ ] `Frame` is the shared contract.
- [ ] Camera sources produce RGB frames.
- [ ] Perception does not know which camera backend produced the frame.
- [ ] Operator detection is separate from gesture recognition.
- [ ] Command/autonomy behavior is not embedded in perception.

## Gesture vocabulary

- [ ] Six target gestures are supported: `THUMBS_UP`, `FIST`, `PALM`, `ONE_FINGER`, `TWO_FINGERS`, `THREE_FINGERS`.
- [ ] `NONE` is supported as rejection/debug class.
- [ ] `NONE` is never emitted as a command event.
- [ ] `ONE_FINGER` means index only, not any one digit.
- [ ] `TWO_FINGERS` means index + middle.
- [ ] `THREE_FINGERS` means index + middle + ring.
- [ ] Middle-only and ring-only are rejected.
- [ ] Thumbs up does not become one finger.

## MediaPipe and geometry

- [ ] MediaPipe runs in `VIDEO` mode.
- [ ] Timestamps are strictly increasing.
- [ ] Canned labels and geometry are computed in parallel.
- [ ] Finger geometry is not fallback-only.
- [ ] `Pointing_Up` and `Victory` remain metadata/hints in v1 and do not override geometry.
- [ ] Raw labels and raw confidences are preserved for debugging.
- [ ] `CANNED`, `GEOMETRY`, and `HYBRID` sources are visible in logs.

## Filtering

- [ ] Confidence filter works.
- [ ] Drop-`NONE` filter works.
- [ ] Stability filter works and resets on absence.
- [ ] Cooldown filter works and uses frame/event timestamps.
- [ ] Filter tests do not require camera or MediaPipe.

## Reproducibility

- [ ] Recorded-media regression suite exists.
- [ ] Model artifact is reproducible via script/checksum or committed artifact policy.
- [ ] CI can run unit tests without camera hardware.
- [ ] CI can run recorded-media tests without camera hardware.
- [ ] Manual live demo procedure is documented.

Final result: `PASS / FAIL`

---

# Phase 5 scaffold addendum

Phase 5 infrastructure can be reviewed separately from full Phase 5 completion.

- [ ] Manifest-driven regression infrastructure exists.
- [ ] A media status checker reports present, missing, required, and optional clips.
- [ ] A recording scaffold exists for future primary, webcam, and RealSense RGB clips.
- [ ] Missing required primary clips are visible and keep Phase 5 at `PARTIAL PASS`.
- [ ] Strict media validation fails when required Phase 5 clips are missing.
- [ ] Optional webcam and RealSense RGB clips do not block ordinary unit tests unless promoted to acceptance requirements.
- [ ] RealSense validation remains deferred until hardware access is available.
- [ ] No fake media has been added, and missing clips are not marked present.

Phase 5 must not be marked `PASS` until the required primary recorded media exists and regression tests run against it.
