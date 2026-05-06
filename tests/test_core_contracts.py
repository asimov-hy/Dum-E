from typing import get_type_hints

import numpy as np
import pytest

from core.frame import Frame, validate_frame
from core.landmarks import Landmark2D, Landmark3D
from core.types import FrameSource
from perception.types import (
    FilterConfig,
    FingerState,
    FingerStateResult,
    GestureEvent,
    GestureObservation,
    GestureServiceConfig,
    GestureSource,
    GestureType,
    MappedGesture,
    OperatorPresence,
)


def test_validate_frame_accepts_valid_rgb_uint8_hwc_contiguous_array() -> None:
    frame = Frame(rgb=np.zeros((8, 10, 3), dtype=np.uint8), timestamp_ms=1)

    validate_frame(frame)


def test_validate_frame_rejects_wrong_ndim() -> None:
    frame = Frame(rgb=np.zeros((8, 10), dtype=np.uint8), timestamp_ms=1)

    with pytest.raises(AssertionError, match="Expected 3D array"):
        validate_frame(frame)


def test_validate_frame_rejects_wrong_channel_count() -> None:
    frame = Frame(rgb=np.zeros((8, 10, 4), dtype=np.uint8), timestamp_ms=1)

    with pytest.raises(AssertionError, match="Expected 3 channels"):
        validate_frame(frame)


def test_validate_frame_rejects_wrong_dtype() -> None:
    frame = Frame(rgb=np.zeros((8, 10, 3), dtype=np.float32), timestamp_ms=1)

    with pytest.raises(AssertionError, match="Expected uint8"):
        validate_frame(frame)


def test_validate_frame_rejects_non_contiguous_array() -> None:
    rgb = np.zeros((8, 10, 3), dtype=np.uint8)[:, ::-1, :]
    frame = Frame(rgb=rgb, timestamp_ms=1)

    with pytest.raises(AssertionError, match="C-contiguous"):
        validate_frame(frame)


def test_frame_accepts_optional_depth_frame_id_and_camera_name() -> None:
    depth_m = np.zeros((8, 10), dtype=np.float32)
    frame = Frame(
        rgb=np.zeros((8, 10, 3), dtype=np.uint8),
        timestamp_ms=42,
        frame_id=7,
        depth_m=depth_m,
        camera_name="phase0-test",
    )

    assert frame.frame_id == 7
    assert frame.depth_m is depth_m
    assert frame.camera_name == "phase0-test"


def test_landmark_contracts_exist_without_backend_types() -> None:
    landmark_2d = Landmark2D(x=0.1, y=0.2, z=-0.3)
    landmark_3d = Landmark3D(x=0.1, y=0.2, z=0.3)

    assert landmark_2d.x == 0.1
    assert landmark_3d.z == 0.3


def test_frame_source_protocol_declares_required_methods() -> None:
    assert {"start", "stop", "get_frame"}.issubset(FrameSource.__dict__)


def test_perception_type_contracts() -> None:
    assert {gesture.name for gesture in GestureType} == {
        "NONE",
        "THUMBS_UP",
        "FIST",
        "PALM",
        "ONE_FINGER",
        "TWO_FINGERS",
        "THREE_FINGERS",
    }
    assert {source.name for source in GestureSource} == {"CANNED", "GEOMETRY", "HYBRID"}

    finger_state = FingerState(
        thumb=False,
        index=True,
        middle=False,
        ring=False,
        pinky=False,
    )
    finger_result = FingerStateResult(
        state=finger_state,
        confidence=0.8,
        margins={"index": 0.2},
    )
    mapped = MappedGesture(
        type=GestureType.ONE_FINGER,
        confidence=0.8,
        source=GestureSource.GEOMETRY,
    )
    observation = GestureObservation(
        type=GestureType.NONE,
        confidence=0.4,
        source=GestureSource.CANNED,
        timestamp_ms=12,
        handedness=None,
        hand_index=0,
        landmarks=(Landmark2D(x=0.1, y=0.2, z=0.0),),
        finger_state_result=finger_result,
    )
    event = GestureEvent(
        type=GestureType.ONE_FINGER,
        confidence=mapped.confidence,
        source=mapped.source,
        timestamp_ms=12,
        handedness="Right",
        hand_index=0,
        finger_state=finger_state,
    )
    presence = OperatorPresence(present=True)

    assert observation.type is GestureType.NONE
    assert event.type is not GestureType.NONE
    assert presence.confidence == 1.0
    assert get_type_hints(FingerState) == {
        "thumb": bool,
        "index": bool,
        "middle": bool,
        "ring": bool,
        "pinky": bool,
    }
    assert "NONE" in (GestureEvent.__doc__ or "")


def test_gesture_service_config_uses_independent_nested_defaults() -> None:
    first = GestureServiceConfig()
    second = GestureServiceConfig()

    assert first.max_num_hands == 1
    assert first.min_hand_detection_confidence == 0.5
    assert first.min_hand_presence_confidence == 0.5
    assert first.min_tracking_confidence == 0.5
    assert first.gesture_config is not second.gesture_config
    assert first.filter_config is not second.filter_config
    assert isinstance(first.gesture_config, type(second.gesture_config))
    assert isinstance(first.filter_config, FilterConfig)
