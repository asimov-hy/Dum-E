# DUM-E MediaPipeline Build Plan v5 (Implementation-Ready)

## Summary

Build the camera and gesture perception layer for DUM-E. The system recognizes six target static hand gestures plus a NONE rejection class, using a hybrid approach: MediaPipe Gesture Recognizer (VIDEO mode) provides canned gesture labels, while custom landmark geometry provides per-finger state. Both signals are computed in parallel for every detected hand, then a priority mapper produces one of seven gesture classes. Camera input is abstracted from the start (webcam, RealSense, or LeRobot adapter). Operator presence is stubbed with a rich interface.

Six target gestures: THUMBS_UP, FIST, PALM, ONE_FINGER, TWO_FINGERS, THREE_FINGERS.
One rejection class: NONE (never emitted as a command event).

Report accuracy over the six targets. Report rejection behavior for NONE separately.

---

## Architecture

```
core/
  frame.py              Frame dataclass, validate_frame()
  types.py              FrameSource protocol
  landmarks.py          Landmark2D, Landmark3D (no MediaPipe dependency)

camera/
  __init__.py
  source.py             Factory function
  opencv_backend.py     OpenCV VideoCapture backend
  realsense_backend.py  RealSense D435 backend (lazy import)
  lerobot_adapter.py    OR: thin wrapper around LeRobot camera classes

perception/
  __init__.py
  types.py              GestureType, GestureSource, MappedGesture,
                         GestureObservation, GestureEvent,
                         FingerState, FingerStateResult,
                         OperatorPresence, GestureConfig,
                         GestureServiceConfig, FilterConfig
  gesture.py            GestureService (analyze_frame, events_from_observations,
                         process_frame)
  finger_state.py       FingerStateDetector
  mapper.py             GestureMapper → MappedGesture
  filters.py            FilterChain (confidence → drop NONE → stability → cooldown)
  operator.py           OperatorDetector protocol + MockOperatorDetector

demos/
  gesture_demo.py       camera → gesture → overlay display
  camera_smoke.py       camera-only smoke test

tests/
  test_core_contracts.py
  test_import_boundaries.py
  test_camera_fake_source.py
  test_gesture_service_timestamp.py
  test_canned_mapper.py
  test_drop_none_filter.py
  test_finger_state_detector.py
  test_gesture_mapper_geometry.py
  test_gesture_mapper_collisions.py
  test_filters_confidence.py
  test_filters_drop_none.py
  test_filters_stability.py
  test_filters_cooldown.py
  test_filters_frame_boundary.py
  test_operator_mock.py
  test_overlay_no_finger_state.py
  test_regression_media.py
```

Import rules:
- `core/` imports nothing from `camera/` or `perception/`.
- `camera/` may import `core/`.
- `perception/` may import `core/`.
- `camera/` and `perception/` do not import each other.
- `demos/` may import all three.
- `autonomy/controller.py` (future) is the only module that wires camera and perception together for robot control.

---

## Core data contracts

All shared types live in `core/`. Both `camera/` and `perception/` import from here. Neither imports the other.

### Frame

`core/frame.py`

```python
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    rgb: np.ndarray                       # uint8, HWC, RGB, C-contiguous
    timestamp_ms: int                     # monotonic, strictly increasing
    frame_id: int | None = None           # monotonic sequence counter
    depth_m: np.ndarray | None = None     # (H, W) float32 meters, or None
    camera_name: str | None = None


def validate_frame(frame: Frame) -> None:
    """Validate the frame data contract. Call in tests and debug mode."""
    assert frame.rgb.ndim == 3, f"Expected 3D array, got {frame.rgb.ndim}D"
    assert frame.rgb.shape[2] == 3, f"Expected 3 channels, got {frame.rgb.shape[2]}"
    assert frame.rgb.dtype == np.uint8, f"Expected uint8, got {frame.rgb.dtype}"
    assert frame.rgb.flags["C_CONTIGUOUS"], "Array must be C-contiguous"
```

- Internal standard is RGB. Convert BGR→RGB at the camera backend boundary, never later.
- Convert RGB→BGR only at the display boundary (cv2.imshow).
- Timestamps: `time.monotonic_ns() // 1_000_000` for live camera.
- For recorded video: `timestamp_ms = round(frame_index * 1000 / fps)`.
- Do not assert a fixed resolution. Warn if negotiated size differs from requested.

### Landmarks

`core/landmarks.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark2D:
    """Normalized image-space landmark. x, y in [0, 1], z is relative depth."""
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Landmark3D:
    """World-space landmark in meters, origin near hand geometric center."""
    x: float
    y: float
    z: float
```

These decouple overlays, regression logs, and serialization from MediaPipe object types. Convert from MediaPipe landmarks to these dataclasses inside `GestureService._build_observations()` — that conversion is a perception concern, not a camera concern.

### FrameSource protocol

`core/types.py`

```python
from typing import Protocol
from core.frame import Frame


class FrameSource(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_frame(self) -> Frame: ...
```

Concrete sources add context-manager support (`__enter__` / `__exit__`).

---

## Perception types

All perception-specific types live in `perception/types.py`.

### GestureType and GestureSource

```python
from enum import Enum


class GestureType(Enum):
    NONE          = "none"            # rejection — never emitted as command event
    THUMBS_UP     = "thumbs_up"       # thumb only, pointing upward
    FIST          = "fist"            # no fingers extended
    PALM          = "palm"            # all/most fingers open
    ONE_FINGER    = "one_finger"      # index only
    TWO_FINGERS   = "two_fingers"     # index + middle
    THREE_FINGERS = "three_fingers"   # index + middle + ring


class GestureSource(Enum):
    CANNED   = "canned"     # classification from MediaPipe label
    GEOMETRY = "geometry"   # classification from finger state patterns
    HYBRID   = "hybrid"     # both signals agreed
```

### MappedGesture

```python
@dataclass(frozen=True)
class MappedGesture:
    type: GestureType
    confidence: float
    source: GestureSource
```

Returned by the mapper. Confidence is derived from the actual signal, not hard-coded.

### FingerState and FingerStateResult

```python
@dataclass(frozen=True)
class FingerState:
    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool


@dataclass(frozen=True)
class FingerStateResult:
    state: FingerState
    confidence: float | None = None       # v1: heuristic or None
    margins: dict[str, float] | None = None  # v1: raw tip-vs-PIP deltas
```

### GestureObservation

```python
@dataclass(frozen=True)
class GestureObservation:
    """Raw observation for every detected hand. Includes NONE.
    Used for overlays, logging, and debugging."""
    type: GestureType
    confidence: float
    source: GestureSource
    timestamp_ms: int
    handedness: str | None
    hand_index: int

    # Present as soon as MediaPipe returns a detected hand.
    landmarks: tuple[Landmark2D, ...] | None = None
    world_landmarks: tuple[Landmark3D, ...] | None = None

    # None in Phase 2; populated once FingerStateDetector exists in Phase 3.
    finger_count: int | None = None
    finger_state: FingerState | None = None
    finger_state_result: FingerStateResult | None = None

    raw_label: str | None = None
    raw_label_confidence: float | None = None
    camera_name: str | None = None
    frame_id: int | None = None
```

Overlay code must treat landmarks and finger state independently:

```python
if obs.landmarks is not None:
    draw_hand_skeleton(frame_bgr, obs.landmarks)

if obs.finger_state_result is not None:
    draw_finger_state(frame_bgr, obs.finger_state_result)

draw_raw_label_and_mapped_type(frame_bgr, obs)
```

### GestureEvent

```python
@dataclass(frozen=True)
class GestureEvent:
    """Filtered, command-relevant event. NONE is never present."""
    type: GestureType                     # never NONE
    confidence: float
    source: GestureSource
    timestamp_ms: int
    handedness: str | None
    hand_index: int
    finger_count: int | None = None
    finger_state: FingerState | None = None
    raw_label: str | None = None
    raw_label_confidence: float | None = None
    camera_name: str | None = None
    frame_id: int | None = None
```

### OperatorPresence

```python
@dataclass(frozen=True)
class OperatorPresence:
    present: bool
    confidence: float = 1.0
    bbox_xyxy: tuple[int, int, int, int] | None = None
```

### Configuration

```python
@dataclass
class GestureConfig:
    semantic_threshold: float = 0.7
    default_geometry_confidence: float = 0.55
    allow_geometry_palm: bool = True
    allow_geometry_fist: bool = True
    # v1: strict. Thumb must be folded for numeric gestures.
    # Future: ThumbState = FOLDED | AMBIGUOUS | EXTENDED trichotomy.


@dataclass
class FilterConfig:
    min_confidence: float = 0.5
    stability_frames: int = 3
    cooldown_seconds: float = 1.0


@dataclass
class GestureServiceConfig:
    model_path: str = "data/models/gesture_recognizer.task"
    max_num_hands: int = 1
    min_hand_detection_confidence: float = 0.5
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    gesture_config: GestureConfig = field(default_factory=GestureConfig)
    filter_config: FilterConfig = field(default_factory=FilterConfig)
```

---

## GestureService API

`perception/gesture.py`

Three public methods. `process_frame` is a convenience that composes the other two.

```python
class GestureService:
    def __init__(self, config: GestureServiceConfig):
        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=config.model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=config.max_num_hands,
            min_hand_detection_confidence=config.min_hand_detection_confidence,
            min_hand_presence_confidence=config.min_hand_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._recognizer = GestureRecognizer.create_from_options(options)
        self._finger_detector = FingerStateDetector()  # wired in Phase 3
        self._mapper = GestureMapper(config.gesture_config)
        self._filters = FilterChain(config.filter_config)
        self._last_timestamp_ms: int = -1

    def analyze_frame(self, frame: Frame) -> list[GestureObservation]:
        """Run inference. Returns all detections including NONE.
        For overlays, logging, debugging."""
        self._enforce_timestamp(frame.timestamp_ms)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame.rgb)
        result = self._recognizer.recognize_for_video(
            mp_image, frame.timestamp_ms
        )
        return self._build_observations(result, frame)

    def events_from_observations(
        self,
        frame: Frame,
        observations: Sequence[GestureObservation],
    ) -> list[GestureEvent]:
        """Filter observations into command-relevant events.
        Does NOT run inference. Safe to call after analyze_frame
        on the same frame."""
        return self._filters.apply(observations, frame=frame)

    def process_frame(self, frame: Frame) -> list[GestureEvent]:
        """Convenience: analyze + filter in one call.
        Do not call both analyze_frame() and process_frame()
        on the same frame — the timestamp guard will raise
        because the timestamp has not increased."""
        observations = self.analyze_frame(frame)
        return self.events_from_observations(frame, observations)

    def close(self) -> None:
        self._recognizer.close()

    def _enforce_timestamp(self, timestamp_ms: int) -> None:
        if timestamp_ms <= self._last_timestamp_ms:
            raise ValueError(
                f"timestamp_ms must be strictly increasing: "
                f"got {timestamp_ms}, previous {self._last_timestamp_ms}"
            )
        self._last_timestamp_ms = timestamp_ms
```

### Observation building (per hand)

```python
    def _build_observations(
        self, result, frame: Frame
    ) -> list[GestureObservation]:
        observations = []
        for i in range(len(result.hand_landmarks)):
            # 1. Raw label and confidence
            raw_label = None
            raw_confidence = 0.0
            if result.gestures and i < len(result.gestures):
                top = result.gestures[i][0]
                raw_label = top.category_name
                raw_confidence = top.score

            # 2. Handedness
            handedness = None
            if result.handedness and i < len(result.handedness):
                handedness = result.handedness[i][0].category_name

            # 3. Convert landmarks to core types
            landmarks_2d = tuple(
                Landmark2D(x=lm.x, y=lm.y, z=lm.z)
                for lm in result.hand_landmarks[i]
            )
            world_lms = None
            if (
                result.hand_world_landmarks
                and i < len(result.hand_world_landmarks)
            ):
                world_lms = tuple(
                    Landmark3D(x=lm.x, y=lm.y, z=lm.z)
                    for lm in result.hand_world_landmarks[i]
                )

            # 4. Finger state (None in Phase 2, populated in Phase 3+)
            fsr = None
            finger_count = None
            finger_state = None
            if self._finger_detector is not None:
                fsr = self._finger_detector.detect(
                    landmarks_2d, world_lms, handedness
                )
                finger_state = fsr.state
                finger_count = sum([
                    fsr.state.thumb, fsr.state.index,
                    fsr.state.middle, fsr.state.ring, fsr.state.pinky,
                ])

            # 5. Map parallel signals
            mapped = self._mapper.map(
                raw_label=raw_label,
                raw_confidence=raw_confidence,
                finger_state_result=fsr,
            )

            # 6. Build observation
            observations.append(GestureObservation(
                type=mapped.type,
                confidence=mapped.confidence,
                source=mapped.source,
                timestamp_ms=frame.timestamp_ms,
                handedness=handedness,
                hand_index=i,
                landmarks=landmarks_2d,
                world_landmarks=world_lms,
                finger_count=finger_count,
                finger_state=finger_state,
                finger_state_result=fsr,
                raw_label=raw_label,
                raw_label_confidence=raw_confidence,
                camera_name=frame.camera_name,
                frame_id=frame.frame_id,
            ))

        return observations
```

### Demo loop pattern

```python
frame = source.get_frame()
observations = gesture.analyze_frame(frame)
events = gesture.events_from_observations(frame, observations)
draw_overlay(frame, observations, events)
handle_events(events)
```

Do not call `process_frame(frame)` after `analyze_frame(frame)` on the same frame.

---

## FilterChain

`perception/filters.py`

Receives Frame for cross-validation. One `apply()` call represents exactly one frame. Observations must not be accumulated across frames.

```python
class FilterChain:
    def __init__(self, config: FilterConfig):
        self._confidence = ConfidenceFilter(config.min_confidence)
        self._drop_none = DropNoneFilter()
        self._stability = StabilityFilter(config.stability_frames)
        self._cooldown = CooldownFilter(config.cooldown_seconds)

    def apply(
        self,
        observations: Sequence[GestureObservation],
        *,
        frame: Frame,
    ) -> list[GestureEvent]:
        # Cross-check: all observations must belong to this frame
        for obs in observations:
            if obs.timestamp_ms != frame.timestamp_ms:
                raise ValueError(
                    "All observations must come from the supplied frame"
                )
            if obs.camera_name != frame.camera_name:
                raise ValueError(
                    "Observation camera_name does not match frame"
                )
            if obs.frame_id is not None and frame.frame_id is not None:
                if obs.frame_id != frame.frame_id:
                    raise ValueError(
                        "Observation frame_id does not match frame"
                    )

        # Filter pipeline
        after_confidence = self._confidence.apply(observations)
        after_none = self._drop_none.apply(after_confidence)
        after_stability = self._stability.apply(
            after_none, timestamp_ms=frame.timestamp_ms
        )
        after_cooldown = self._cooldown.apply(
            after_stability, timestamp_ms=frame.timestamp_ms
        )

        # Notify stability filter of all active keys this frame
        # so absent keys get their streaks reset
        present_keys = {
            (obs.type, obs.handedness, obs.camera_name)
            for obs in after_none
        }
        self._stability.reset_absent_keys(present_keys)

        # Convert surviving observations to events
        return [self._to_event(obs) for obs in after_cooldown]

    @staticmethod
    def _to_event(obs: GestureObservation) -> GestureEvent:
        return GestureEvent(
            type=obs.type,
            confidence=obs.confidence,
            source=obs.source,
            timestamp_ms=obs.timestamp_ms,
            handedness=obs.handedness,
            hand_index=obs.hand_index,
            finger_count=obs.finger_count,
            finger_state=obs.finger_state,
            raw_label=obs.raw_label,
            raw_label_confidence=obs.raw_label_confidence,
            camera_name=obs.camera_name,
            frame_id=obs.frame_id,
        )
```

### Stability filter

Key: `(type, handedness, camera_name)`. Does NOT include `raw_label` or `finger_count`.

Reset rules:
- If a key is absent from the current frame's post-NONE-filter observations, reset that key's streak.
- If the frame has no observations (empty list), reset all active streaks.
- A missing frame is a break, not a pause.

### Cooldown filter

Uses `timestamp_ms` from the frame, not `time.time()`. Deterministic for recorded-video regression tests.

---

## GestureMapper

`perception/mapper.py`

Full signature accepts `FingerStateResult | None` so Phase 2 can call it without finger state.

```python
class GestureMapper:
    def __init__(self, config: GestureConfig):
        self._config = config

    def map(
        self,
        *,
        raw_label: str | None,
        raw_confidence: float,
        finger_state_result: FingerStateResult | None,
    ) -> MappedGesture:
        c = self._config
        fs = finger_state_result.state if finger_state_result else None
        geo_conf = (
            finger_state_result.confidence
            if finger_state_result and finger_state_result.confidence is not None
            else c.default_geometry_confidence
        )

        # --- Priority 1–3: Semantic canned gestures ---

        if raw_label == "Thumb_Up" and raw_confidence >= c.semantic_threshold:
            hybrid = (
                fs is not None
                and fs.thumb
                and not fs.index
                and not fs.middle
                and not fs.ring
                and not fs.pinky
            )
            return MappedGesture(
                type=GestureType.THUMBS_UP,
                confidence=raw_confidence,
                source=GestureSource.HYBRID if hybrid else GestureSource.CANNED,
            )

        if raw_label == "Closed_Fist" and raw_confidence >= c.semantic_threshold:
            hybrid = (
                fs is not None
                and not any([fs.thumb, fs.index, fs.middle, fs.ring, fs.pinky])
            )
            return MappedGesture(
                type=GestureType.FIST,
                confidence=raw_confidence,
                source=GestureSource.HYBRID if hybrid else GestureSource.CANNED,
            )

        if raw_label == "Open_Palm" and raw_confidence >= c.semantic_threshold:
            hybrid = (
                fs is not None
                and fs.index and fs.middle and fs.ring and fs.pinky
            )
            return MappedGesture(
                type=GestureType.PALM,
                confidence=raw_confidence,
                source=GestureSource.HYBRID if hybrid else GestureSource.CANNED,
            )

        # --- Priority 4–6: Pattern-based canonical gestures ---

        if fs is not None:
            # Thumb must be folded for numeric gestures (v1 strict rule)
            thumb_ok = not fs.thumb

            if fs.index and not fs.middle and not fs.ring and not fs.pinky and thumb_ok:
                return MappedGesture(
                    type=GestureType.ONE_FINGER,
                    confidence=geo_conf,
                    source=GestureSource.GEOMETRY,
                )

            if fs.index and fs.middle and not fs.ring and not fs.pinky and thumb_ok:
                return MappedGesture(
                    type=GestureType.TWO_FINGERS,
                    confidence=geo_conf,
                    source=GestureSource.GEOMETRY,
                )

            if fs.index and fs.middle and fs.ring and not fs.pinky and thumb_ok:
                return MappedGesture(
                    type=GestureType.THREE_FINGERS,
                    confidence=geo_conf,
                    source=GestureSource.GEOMETRY,
                )

            # --- Priority 7–8: Geometry fallbacks ---

            if (
                not any([fs.thumb, fs.index, fs.middle, fs.ring, fs.pinky])
                and c.allow_geometry_fist
            ):
                return MappedGesture(
                    type=GestureType.FIST,
                    confidence=geo_conf,
                    source=GestureSource.GEOMETRY,
                )

            if (
                fs.index and fs.middle and fs.ring and fs.pinky
                and c.allow_geometry_palm
            ):
                return MappedGesture(
                    type=GestureType.PALM,
                    confidence=geo_conf,
                    source=GestureSource.GEOMETRY,
                )

        # --- Priority 9: Nothing matched ---

        return MappedGesture(
            type=GestureType.NONE,
            confidence=0.0,
            source=GestureSource.GEOMETRY,
        )
```

### Priority order rationale

1. THUMBS_UP — geometrically one extended digit; must not become ONE_FINGER.
2. FIST (canned) — whole-hand state, named command.
3. PALM (canned) — whole-hand state, named command.
4. ONE_FINGER — index only, geometry.
5. TWO_FINGERS — index + middle, geometry.
6. THREE_FINGERS — index + middle + ring, geometry.
7. FIST (geometry fallback) — when canned label missed it.
8. PALM (geometry fallback) — when canned label missed it. Four fingers (no thumb) maps here intentionally.
9. NONE — unrecognized or ambiguous.

### Canned label handling for Pointing_Up and Victory

v1: metadata only. Preserved as `raw_label` on the observation. Do not override geometry.
v2 (future): use as tie-breakers when FingerStateResult margins show geometry is uncertain.

### Explicit design decisions

- **Four fingers (no thumb):** Maps to PALM via geometry fallback. Intentional.
- **Thumb strict:** Must be folded for numeric gestures in v1. Future: `ThumbState = FOLDED | AMBIGUOUS | EXTENDED` trichotomy if strict proves too brittle.
- **Open_Palm carries metadata:** `finger_count=5`, `finger_state` with all True. Command layer can distinguish semantic palm from geometric count.
- **Closed_Fist is first-class.** FIST, not NONE.

---

## FingerStateDetector

`perception/finger_state.py`

### v1: image-space landmark heuristic

```python
class FingerStateDetector:
    def detect(
        self,
        landmarks: tuple[Landmark2D, ...],
        world_landmarks: tuple[Landmark3D, ...] | None,
        handedness: str | None,
    ) -> FingerStateResult:
        ...
```

v1 uses image landmarks (Landmark2D) for the tip-vs-PIP heuristic. World landmarks (Landmark3D) are stored on the observation but not used for classification in v1. They are reserved for v2 angle-based geometry.

For index, middle, ring, pinky: extended if `tip.y < pip.y` (image space, y down).

For thumb: compare `tip.x` vs `ip.x`, accounting for handedness.
- Left hand: extended if `tip.x < ip.x`.
- Right hand: extended if `tip.x > ip.x`.

v1 populates FingerStateResult with:
- `state`: boolean per-finger decisions.
- `confidence`: simple heuristic (e.g., average absolute margin magnitude normalized), or None.
- `margins`: dict of raw tip-vs-PIP deltas per finger for logging and future calibration.

### Known limitations

- Works for upright hands facing the camera.
- Degrades with rotation >30°, tilted wrists, side views.
- Ring finger is least reliable (partial occlusion). Known risk for THREE_FINGERS oscillation with TWO_FINGERS. Mitigated by stability filter.

### v2 roadmap

- Angle-based logic: PIP joint angle + distance-from-wrist.
- Use world landmarks in meters.
- Calibrated confidence from margins.
- Pointing_Up and Victory as tie-breakers when geometry uncertain.
- ThumbState trichotomy if strict rule proves too brittle.

### Mirrored webcam policy

Never flip frames before inference. Flip only for display.

---

## OperatorDetector

`perception/operator.py`

```python
class OperatorDetector(Protocol):
    def detect(self, frame: Frame) -> OperatorPresence: ...


class MockOperatorDetector:
    def detect(self, frame: Frame) -> OperatorPresence:
        return OperatorPresence(present=True, confidence=1.0, bbox_xyxy=None)
```

Separate gate from gesture recognition. Autonomy controller checks operator presence and gesture events independently.

---

## Phases

### Phase 0 — Package skeleton and shared contracts

**Goal:** Establish shared types and import boundaries before any camera or MediaPipe code.

**Create:**

```
core/frame.py
core/types.py
core/landmarks.py
camera/__init__.py
perception/__init__.py
perception/types.py
tests/test_core_contracts.py
tests/test_import_boundaries.py
```

**Tasks:**

1. Frame dataclass with validate_frame().
2. Landmark2D, Landmark3D dataclasses.
3. FrameSource protocol.
4. GestureType, GestureSource, GestureConfig, FilterConfig, GestureServiceConfig enums and dataclasses.
5. FingerState, FingerStateResult dataclasses.
6. GestureObservation, GestureEvent, MappedGesture dataclasses.
7. OperatorPresence dataclass.
8. Import boundary tests: verify core imports nothing from camera or perception; camera and perception do not import each other.

**Tests:**

- `test_core_contracts.py`: Frame validator catches non-RGB, non-uint8, non-contiguous, wrong ndim inputs.
- `test_import_boundaries.py`: import each package, verify no cross-imports.

**Phase gate:** Passes without installing MediaPipe, OpenCV, RealSense, or LeRobot.

---

### Phase 1 — Camera sources

**Goal:** Get RGB Frame objects flowing from one source with reliable timestamps and cleanup.

**Create:**

```
camera/opencv_backend.py
camera/realsense_backend.py      # optional, lazy import
camera/lerobot_adapter.py        # optional
camera/source.py                 # factory
demos/camera_smoke.py
tests/test_camera_fake_source.py
```

**Tasks:**

1. OpenCV backend: open device, read BGR, convert to RGB at boundary, ensure C-contiguous uint8 HWC, attach monotonic timestamp_ms and frame_id, release in stop() and __exit__().

2. RealSense backend: lazy import (inside `start()`). Provides depth_m. Same conventions.

3. LeRobot adapter: if integrating with LeRobot, wrap existing OpenCVCamera / RealSenseCamera via FrameSource protocol. Do not duplicate their connection or cleanup logic.

4. Factory: `create_source(backend: str = "webcam") -> FrameSource`.

5. FakeSource for tests: yields pre-built Frame objects, no hardware.

**Tests:**

- `test_camera_fake_source.py`: FakeSource produces valid frames, timestamps increase, frame_ids increase, validate_frame passes.
- Manual: `python demos/camera_smoke.py --source webcam --frames 100` — 100 frames, FPS printed, resolution printed, cv2.imshow works after RGB→BGR.
- Manual (if available): `python demos/camera_smoke.py --source realsense --frames 100` — depth_m present.
- Context manager releases device on exit.

**Phase gate:** Camera works independently of MediaPipe.

---

### Phase 2 — MediaPipe canned semantic gestures

**Goal:** Integrate MediaPipe in VIDEO mode. Recognize three canned semantic targets: THUMBS_UP, PALM, FIST.

**Create:**

```
perception/gesture.py
perception/mapper.py
perception/filters.py            # DropNoneFilter only
demos/gesture_demo.py            # Phase 2 version
tests/test_gesture_service_timestamp.py
tests/test_canned_mapper.py
tests/test_drop_none_filter.py
tests/test_overlay_no_finger_state.py
data/models/gesture_recognizer.task
scripts/download_gesture_model.py
```

**Tasks:**

1. Download gesture_recognizer.task (~5MB). Store in data/models/. Pin path in config. Download script + SHA-256 verification. No runtime download.

2. GestureService with analyze_frame(), events_from_observations(), process_frame(). Timestamp guard enforcing strictly increasing timestamp_ms.

3. Model path validation on init.

4. Phase 2 mapper: canned labels only.
   - `Thumb_Up` → THUMBS_UP (source=CANNED)
   - `Open_Palm` → PALM (source=CANNED)
   - `Closed_Fist` → FIST (source=CANNED)
   - Everything else → NONE (source=CANNED)
   - `finger_state_result` is None; geometry branches do not fire.

5. DropNoneFilter only. Full filter chain in Phase 4.

6. _build_observations: landmarks converted to Landmark2D/3D. finger_state and finger_state_result are None.

7. Demo overlay: draws hand skeleton from landmarks, shows raw_label and mapped type. Does NOT crash when finger_state_result is None. Finger-state panel hidden or displays "not available."

**Tests:**

- `test_gesture_service_timestamp.py`: non-increasing timestamp raises ValueError.
- `test_canned_mapper.py`: Thumb_Up→THUMBS_UP, Open_Palm→PALM, Closed_Fist→FIST, Victory→NONE, None→NONE.
- `test_drop_none_filter.py`: NONE observations dropped, target gestures pass through.
- `test_overlay_no_finger_state.py`: observation with landmarks but finger_state_result=None renders skeleton without crash.
- Manual: thumbs up → Observation THUMBS_UP, Event THUMBS_UP.
- Manual: open palm → Observation PALM, Event PALM.
- Manual: closed fist → Observation FIST, Event FIST.
- Manual: Thumb_Down → Observation NONE, no Event.
- Manual: no hand → empty lists.
- Manual: per-frame latency printed.

**Phase gate:** Semantic canned gestures work before any custom finger geometry exists.

---

### Phase 3 — Finger-state geometry and full mapper

**Goal:** Compute which fingers are extended. Map canonical numeric hand shapes. Extend mapper with HYBRID source logic.

**Create:**

```
perception/finger_state.py
tests/test_finger_state_detector.py
tests/test_gesture_mapper_geometry.py
tests/test_gesture_mapper_collisions.py
```

**Tasks:**

1. FingerStateDetector: v1 image-space heuristic. Returns FingerStateResult with state, optional confidence, optional margins.

2. Extend mapper: full priority mapping with HYBRID source when canned label and geometry agree.

3. Wire FingerStateDetector into GestureService._build_observations. For every hand with landmarks, always compute FingerStateResult. Finger state is never gated on canned label being None.

4. Mapper signature unchanged from Phase 2 (finger_state_result was already optional). Phase 3 starts passing it.

**Mapper collision tests (mandatory):**

| raw_label | finger_state | Expected type | Expected source |
|---|---|---|---|
| Thumb_Up | thumb only | THUMBS_UP | HYBRID |
| Thumb_Up | bad geometry | THUMBS_UP | CANNED |
| Closed_Fist | all false | FIST | HYBRID |
| Closed_Fist | bad geometry | FIST | CANNED |
| Open_Palm | all/four fingers | PALM | HYBRID |
| Open_Palm | bad geometry | PALM | CANNED |
| Pointing_Up | index only | ONE_FINGER | GEOMETRY |
| Victory | index + middle | TWO_FINGERS | GEOMETRY |
| None | index + middle + ring | THREE_FINGERS | GEOMETRY |
| None | middle only | NONE | GEOMETRY |
| None | index + middle + ring + pinky | PALM | GEOMETRY |
| Thumb_Down | thumb only | NONE | GEOMETRY |
| None | thumb + index | NONE | GEOMETRY |

**Debug outputs per observation:**

```
raw_label, raw_label_confidence, mapped_type, source,
finger_state (5 bools), finger_count, per-finger margins,
handedness, frame_id, timestamp_ms
```

**Manual validation:**

- 1 finger (index) → ONE_FINGER.
- 2 fingers (index + middle) → TWO_FINGERS.
- 3 fingers (index + middle + ring) → THREE_FINGERS.
- Thumbs up → THUMBS_UP, not ONE_FINGER.
- Open palm → PALM.
- Closed fist → FIST.
- Middle finger only → NONE.
- Four fingers (no thumb) → PALM fallback.
- Thumb + index → NONE.
- Ring finger oscillation: hold three fingers and observe flicker frequency.
  Document the behavior. This was expected before Phase 4; current Phase 4
  stability/cooldown filters exist but do not prove camera-specific reliability.

**Phase gate:** All six target gestures plus NONE rejection work without filters.

---

### Phase 4 — Full filter chain and operator stub

**Goal:** Suppress accidental triggers. Separate perception from command authorization.

**Create:**

```
perception/operator.py
tests/test_filters_confidence.py
tests/test_filters_drop_none.py
tests/test_filters_stability.py
tests/test_filters_cooldown.py
tests/test_filters_frame_boundary.py
tests/test_operator_mock.py
```

**Tasks:**

1. Full FilterChain: confidence → drop NONE → stability → cooldown.

2. FilterChain.apply() receives Frame for cross-validation. Asserts all observations match frame timestamp, camera_name, and frame_id.

3. Stability filter:
   - Key: `(type, handedness, camera_name)`.
   - Does NOT include raw_label or finger_count.
   - Reset rules:
     - Key absent from current frame → reset that key's streak.
     - Empty observations (no hands) → reset all active streaks.
     - Observation mapped to NONE → already dropped before stability.
     - Observation confidence-filtered → does not advance stability.
     - Missing frame = break, not pause.

4. Cooldown filter: uses `timestamp_ms` from frame. Deterministic for recorded video.

5. MockOperatorDetector: always returns present=True. Separate gate.

**Tests (all synthetic, no camera):**

- `test_filters_confidence.py`: low-confidence observations dropped.
- `test_filters_drop_none.py`: NONE observations dropped, targets pass.
- `test_filters_stability.py`:
  - THUMBS_UP repeated 3 frames → one Event on frame 3.
  - THUMBS_UP held 10 frames → no duplicate during cooldown.
  - TWO_FINGERS, TWO_FINGERS, no hand, TWO_FINGERS → no event; streak reset.
  - Victory/None raw_label flicker with stable TWO_FINGERS geometry → stabilizes.
  - PALM then FIST → independent keys.
- `test_filters_cooldown.py`:
  - Cooldown uses event timestamp, deterministic.
  - Different keys cool down independently.
- `test_filters_frame_boundary.py`:
  - Matching timestamps pass.
  - Mixed timestamps raise ValueError.
  - Mismatched camera_name raises ValueError.
  - Empty observations reset stability streaks.
- `test_operator_mock.py`: MockOperatorDetector returns present=True.

**Manual validation:**

- Casual hand movement → no events.
- Deliberate gesture held steady → event after N frames.
- Held gesture → no repeated events within cooldown.
- Switch gesture → new event after stability.
- Hand leaves frame → streak resets.

**Debug outputs per frame:**

```
confidence_pass/drop
none_drop
stability_count x/N
cooldown_pass/drop
emitted events
```

**Phase gate:** Live demo produces stable, non-spammy command events.

---

### Phase 5 — Demo, recording, regression suite, and packaging

**Goal:** Make the prototype reproducible without a live camera.

**Create:**

```
demos/gesture_demo.py            # final version
scripts/download_gesture_model.py
tests/test_regression_media.py
data/test_media/                 # recorded clips
```

**Demo script** (`demos/gesture_demo.py`):

```
--source webcam|realsense|video:<path>
--show-flipped-display true|false
--log-observations
--log-events
--draw-landmarks
--draw-finger-state
--draw-filter-state
```

Demo loop:

```python
frame = source.get_frame()
observations = gesture.analyze_frame(frame)
events = gesture.events_from_observations(frame, observations)
draw_overlay(frame, observations, events)
handle_events(events)
```

Clean exit on `q` or Ctrl+C.

**Regression media to record:**

- Clear thumbs up
- Clear fist
- Clear palm
- Index only
- Index + middle
- Index + middle + ring
- Middle only
- Ring only
- Thumb + index
- Four fingers, thumb folded
- No hand
- Partial hand entering/leaving
- Poor lighting
- Motion blur
- Two hands visible (verify graceful handling with max_num_hands=1)
- Thumbs up from side angle
- Three-finger ring-finger stress case
- Victory/None oscillation sequence

**Regression test suite** (`test_regression_media.py`):

Each clip reports:
- Target class
- Observed events
- First detection timestamp
- Misses
- False positives
- NONE rejection behavior
- Raw label distribution
- Source distribution (CANNED / GEOMETRY / HYBRID)

**Metrics:**

- Accuracy over six target gestures (per-class).
- False-positive rate for NONE cases.
- Latency per frame (ms).
- Time-to-event after stability filter (frames and ms).

**Packaging:**

```toml
[project.optional-dependencies]
camera = ["opencv-python", "numpy"]
perception = ["mediapipe>=0.10", "opencv-python", "numpy"]
realsense = ["pyrealsense2"]
dev = ["pytest", "numpy"]
```

**Model management:**

```
scripts/download_gesture_model.py    # downloads + SHA-256 verification
data/models/gesture_recognizer.task  # local, not runtime-downloaded
data/models/gesture_recognizer.task.sha256
```

**Phase gate:** CI runs unit tests and recorded-media regression tests without a physical camera.

---

## Phase dependency map

```
Phase 0: no external runtime deps
  ↓
Phase 1: OpenCV / camera only
  ↓
Phase 2: MediaPipe canned gestures only
  ↓
Phase 3: custom geometry + mapper
  ↓
Phase 4: filters + operator stub
  ↓
Phase 5: demo + recorded regression + packaging
```

Each phase has a separate failure surface:
- Phase 0: contract / import issues.
- Phase 1: camera / timestamp / color issues.
- Phase 2: MediaPipe / model / raw-label issues.
- Phase 3: landmark geometry / mapping issues.
- Phase 4: temporal filtering issues.
- Phase 5: reproducibility / demo / package issues.

---

## Validation matrix

| Pose | Expected type | Likely raw_label | Expected finger_state | Source | Notes |
|---|---|---|---|---|---|
| Thumbs up | THUMBS_UP | Thumb_Up | thumb=T, rest=F | HYBRID | Must not become ONE_FINGER |
| Closed fist | FIST | Closed_Fist | all False | HYBRID | First-class command |
| Open palm | PALM | Open_Palm | all True | HYBRID | Carries finger_count=5 |
| Index only | ONE_FINGER | Pointing_Up or None | index=T, rest=F | GEOMETRY | Canned label is metadata only |
| Index + middle | TWO_FINGERS | Victory or None | index=T, middle=T, rest=F | GEOMETRY | Canned label is metadata only |
| Index + middle + ring | THREE_FINGERS | None | idx=T, mid=T, ring=T, rest=F | GEOMETRY | No canned match |
| Middle only | NONE | None | middle=T, rest=F | — | Not a valid command |
| Ring only | NONE | None | ring=T, rest=F | — | Not a valid command |
| Four fingers (no thumb) | PALM (fallback) | None or Open_Palm | idx/mid/ring/pinky=T, thumb=F | GEOMETRY | Intentional |
| Thumb + index | NONE | None | thumb=T, index=T, rest=F | — | Not in vocabulary |
| No hand | (no event) | — | — | — | Empty list |
| Thumb_Down | NONE | Thumb_Down | varies | — | Dropped by DropNoneFilter |
| Victory/None oscillation | TWO_FINGERS | varies | index=T, middle=T | GEOMETRY | Stability key ignores raw_label |

---

## Known risks

**Ring finger reliability.** Partial occlusion → THREE_FINGERS oscillation. Stability filter mitigates but increases latency.

**Thumb relaxation.** Strict v1 default will reject some valid poses. Monitor rejection rate. Future: ThumbState trichotomy.

**Camera angle sensitivity.** v1 tip-vs-PIP heuristic degrades >30° rotation. v2 angle-based approach addresses this.

**Mirrored display vs inference.** Never flip before inference.

**Resolution negotiation.** Validate contract, warn on size mismatch, do not crash.

---

## Decision log

| Decision | Chosen | Rationale |
|---|---|---|
| Frame location | `core/frame.py` | Shared contract; no perception→camera dependency |
| Landmark types | `core/landmarks.py` | Decouples overlays/logs from MediaPipe types |
| API shape | `analyze_frame` + `events_from_observations` + `process_frame` | No duplicate inference; overlays see observations, control sees events |
| Filter input | Frame passed to FilterChain | Cross-validates timestamps; handles empty-frame resets |
| Mapper output | `MappedGesture(type, confidence, source)` | No hard-coded confidence; source aids debugging |
| HYBRID source | Canned + geometry agreement | Higher confidence signal; visible in logs |
| MediaPipe mode | VIDEO (sync) | Maps to analyze_frame(). LIVE_STREAM reserved for async |
| Signal processing | Parallel, not fallback | Both signals always computed for every hand |
| Vocabulary | Six targets + NONE | Explicit classes, not generic FINGER_COUNT(N) |
| Finger detection | Pattern-based (which fingers) | Not count-based; prevents middle→ONE_FINGER |
| Thumb rule | Strict v1; ThumbState trichotomy in v2 | Not "ignore thumb" — that allows thumb+index=ONE_FINGER |
| Canned hints | v1: metadata only; v2: tie-breakers | Geometry decides in v1 |
| Return type | `list[...]` | Multi-hand ready; `max_num_hands=1` for prototype |
| Frame format | RGB internally | Convert at camera boundary only |
| Stability key | `(type, handedness, camera_name)` | Excludes raw_label; handles classifier flicker |
| Stability reset | On absence, empty frame, NONE, confidence drop | Missing frames break streaks |
| Cooldown timing | `event.timestamp_ms` | Deterministic for recorded-video tests |
| Filter order | confidence → NONE → stability → cooldown | NONE never reaches stability counter |
| FingerStateResult | Booleans + optional confidence/margins | v1 simple; v2 calibrates without API break |
| Landmarks in v1 | Image-space for classification | World landmarks stored, reserved for v2 |
| Confidence params | All three MediaPipe thresholds | detection + presence + tracking |
| Operator naming | OperatorDetector | Unambiguous in robotics |
| Four fingers | PALM via geometry fallback | Intentional; documented |
| Resolution | Assert contract, warn on size | Do not crash on negotiated resolution |
| Phase 0 | Package skeleton first | Import boundaries verified before any external deps |
| Model storage | Download script + SHA-256 | No runtime download; local path in config |
| Prototype camera | Standalone OpenCV first | LeRobot adapter behind same FrameSource protocol |

---

## Implementation decisions locked

1. Standalone OpenCV first. LeRobot adapter behind FrameSource protocol.
2. Download script + SHA-256 for model bundle. No runtime download.
3. Thumb strict in v1. No "ignore thumb." ThumbState trichotomy later if needed.
4. max_num_hands=1 for prototype. Return types stay as lists.
5. Pointing_Up and Victory are metadata only in v1.

---

## Phase 5 scaffold status addendum

Phase 5 infrastructure is present, but Phase 5 is not a full PASS until real recorded regression media exists and the regression suite runs against it.

- Primary manifest-driven regression entries are required for Phase 5 completion.
- Missing required primary clips keep Phase 5 at PARTIAL PASS.
- Webcam and RealSense RGB camera-specific suites are supported as compatibility/acceptance suites.
- Optional camera-specific clips do not block ordinary unit tests unless strict media validation or acceptance policy requires them.
- RealSense validation and RealSense RGB regression capture are deferred until camera access is available.
- See `docs/mediapipeline_current_state.md` and `docs/mediapipeline_recording_plan.md` for the current status and capture procedure.
