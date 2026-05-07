import pytest

from core.landmarks import Landmark2D, Landmark3D
from perception.finger_state import FingerStateDetector
from perception.types import FingerStateResult


def test_detector_accepts_core_landmark_tuples_world_landmarks_and_handedness() -> None:
    detector = FingerStateDetector()
    landmarks = _landmarks(index=True)
    world_landmarks = tuple(Landmark3D(x=0.0, y=0.0, z=0.0) for _ in range(21))

    result = detector.detect(landmarks, world_landmarks, "Right")

    assert isinstance(result, FingerStateResult)
    assert result.state.index is True
    assert result.confidence is None
    assert result.margins is not None
    assert set(result.margins) == {"thumb", "index", "middle", "ring", "pinky"}


def test_invalid_landmark_count_raises_clear_error() -> None:
    detector = FingerStateDetector()

    with pytest.raises(ValueError, match="Expected at least 21 hand landmarks"):
        detector.detect(tuple(Landmark2D(x=0.0, y=0.0, z=0.0) for _ in range(20)), None, "Right")


@pytest.mark.parametrize(
    ("name", "kwargs", "expected"),
    [
        ("thumb only", {"thumb": True}, (True, False, False, False, False)),
        ("closed fist", {}, (False, False, False, False, False)),
        ("open palm", {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}, (True, True, True, True, True)),
        ("index only", {"index": True}, (False, True, False, False, False)),
        ("index middle", {"index": True, "middle": True}, (False, True, True, False, False)),
        ("index middle ring", {"index": True, "middle": True, "ring": True}, (False, True, True, True, False)),
        ("middle only", {"middle": True}, (False, False, True, False, False)),
        ("ring only", {"ring": True}, (False, False, False, True, False)),
        ("thumb index", {"thumb": True, "index": True}, (True, True, False, False, False)),
        ("four fingers", {"index": True, "middle": True, "ring": True, "pinky": True}, (False, True, True, True, True)),
    ],
)
def test_synthetic_finger_states(
    name: str,
    kwargs: dict[str, bool],
    expected: tuple[bool, bool, bool, bool, bool],
) -> None:
    del name
    result = FingerStateDetector().detect(_landmarks(**kwargs), None, "Right")

    assert _state_tuple(result) == expected


def test_left_hand_thumb_behavior() -> None:
    result = FingerStateDetector().detect(_landmarks(thumb=True, handedness="Left"), None, "Left")

    assert result.state.thumb is True
    assert result.margins["thumb"] > 0


def test_right_hand_thumb_behavior() -> None:
    result = FingerStateDetector().detect(_landmarks(thumb=True, handedness="Right"), None, "Right")

    assert result.state.thumb is True
    assert result.margins["thumb"] > 0


def test_unknown_handedness_uses_conservative_thumb_policy() -> None:
    result = FingerStateDetector().detect(_landmarks(thumb=True), None, None)

    assert result.state.thumb is False
    assert result.margins["thumb"] <= 0


def _state_tuple(result: FingerStateResult) -> tuple[bool, bool, bool, bool, bool]:
    state = result.state
    return state.thumb, state.index, state.middle, state.ring, state.pinky


def _landmarks(
    *,
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    handedness: str = "Right",
) -> tuple[Landmark2D, ...]:
    landmarks = [Landmark2D(x=0.5, y=0.5, z=0.0) for _ in range(21)]
    normalized = handedness.lower()
    thumb_ip_x = 0.6 if normalized == "left" else 0.4
    landmarks[3] = Landmark2D(x=thumb_ip_x, y=0.5, z=0.0)
    if normalized == "left":
        thumb_tip_x = thumb_ip_x - 0.1 if thumb else thumb_ip_x + 0.1
    else:
        thumb_tip_x = thumb_ip_x + 0.1 if thumb else thumb_ip_x - 0.1
    landmarks[4] = Landmark2D(x=thumb_tip_x, y=0.5, z=0.0)

    _set_vertical_finger(landmarks, pip_index=6, tip_index=8, extended=index)
    _set_vertical_finger(landmarks, pip_index=10, tip_index=12, extended=middle)
    _set_vertical_finger(landmarks, pip_index=14, tip_index=16, extended=ring)
    _set_vertical_finger(landmarks, pip_index=18, tip_index=20, extended=pinky)
    return tuple(landmarks)


def _set_vertical_finger(
    landmarks: list[Landmark2D],
    *,
    pip_index: int,
    tip_index: int,
    extended: bool,
) -> None:
    landmarks[pip_index] = Landmark2D(x=0.5, y=0.5, z=0.0)
    landmarks[tip_index] = Landmark2D(x=0.5, y=0.4 if extended else 0.6, z=0.0)
