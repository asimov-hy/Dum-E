"""Perception data contracts for DUM-E MediaPipeline Phase 0."""

from dataclasses import dataclass, field
from enum import Enum

from core.landmarks import Landmark2D, Landmark3D


class GestureType(Enum):
    """Supported gestures.

    ``NONE`` is a rejection-only class and must never be emitted as a
    command-relevant ``GestureEvent``.
    """

    NONE = "none"
    THUMBS_UP = "thumbs_up"
    FIST = "fist"
    PALM = "palm"
    ONE_FINGER = "one_finger"
    TWO_FINGERS = "two_fingers"
    THREE_FINGERS = "three_fingers"


class GestureSource(Enum):
    """Origin of a mapped gesture decision."""

    CANNED = "canned"
    GEOMETRY = "geometry"
    HYBRID = "hybrid"


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
    confidence: float | None = None
    margins: dict[str, float] | None = None


@dataclass(frozen=True)
class MappedGesture:
    type: GestureType
    confidence: float
    source: GestureSource


@dataclass(frozen=True)
class GestureObservation:
    """Raw observation for a detected hand.

    Observations are used for overlays, logs, and debugging, and may include
    ``GestureType.NONE``.
    """

    type: GestureType
    confidence: float
    source: GestureSource
    timestamp_ms: int
    handedness: str | None
    hand_index: int
    landmarks: tuple[Landmark2D, ...] | None = None
    world_landmarks: tuple[Landmark3D, ...] | None = None
    finger_count: int | None = None
    finger_state: FingerState | None = None
    finger_state_result: FingerStateResult | None = None
    raw_label: str | None = None
    raw_label_confidence: float | None = None
    camera_name: str | None = None
    frame_id: int | None = None


@dataclass(frozen=True)
class GestureEvent:
    """Filtered, command-relevant event.

    ``GestureType.NONE`` must never be emitted as a ``GestureEvent``.
    """

    type: GestureType
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


@dataclass(frozen=True)
class OperatorPresence:
    present: bool
    confidence: float = 1.0
    bbox_xyxy: tuple[int, int, int, int] | None = None


@dataclass
class GestureConfig:
    semantic_threshold: float = 0.7
    default_geometry_confidence: float = 0.55
    allow_geometry_palm: bool = True
    allow_geometry_fist: bool = True


@dataclass
class FilterConfig:
    min_confidence: float = 0.5
    stability_frames: int = 3
    cooldown_seconds: float = 1.0


@dataclass
class GestureServiceConfig:
    model_path: str = "data/mediapipe/models/gesture_recognizer.task"
    max_num_hands: int = 1
    min_hand_detection_confidence: float = 0.5
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    gesture_config: GestureConfig = field(default_factory=GestureConfig)
    filter_config: FilterConfig = field(default_factory=FilterConfig)
