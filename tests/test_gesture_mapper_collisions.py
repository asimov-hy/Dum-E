import pytest

from perception.mapper import GestureMapper
from perception.types import FingerState, FingerStateResult, GestureSource, GestureType


def _state(
    *,
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
) -> FingerStateResult:
    return FingerStateResult(
        state=FingerState(
            thumb=thumb,
            index=index,
            middle=middle,
            ring=ring,
            pinky=pinky,
        ),
        confidence=0.8,
        margins=None,
    )


@pytest.mark.parametrize(
    ("raw_label", "finger_state", "expected_type", "expected_source"),
    [
        ("Thumb_Up", _state(thumb=True), GestureType.THUMBS_UP, GestureSource.HYBRID),
        ("Thumb_Up", _state(index=True), GestureType.THUMBS_UP, GestureSource.CANNED),
        ("Closed_Fist", _state(), GestureType.FIST, GestureSource.HYBRID),
        ("Closed_Fist", _state(index=True), GestureType.FIST, GestureSource.CANNED),
        (
            "Open_Palm",
            _state(index=True, middle=True, ring=True, pinky=True),
            GestureType.PALM,
            GestureSource.HYBRID,
        ),
        ("Open_Palm", _state(index=True), GestureType.PALM, GestureSource.CANNED),
        (
            "Pointing_Up",
            _state(index=True),
            GestureType.ONE_FINGER,
            GestureSource.GEOMETRY,
        ),
        (
            "Victory",
            _state(index=True, middle=True),
            GestureType.TWO_FINGERS,
            GestureSource.GEOMETRY,
        ),
        (
            None,
            _state(index=True, middle=True, ring=True),
            GestureType.THREE_FINGERS,
            GestureSource.GEOMETRY,
        ),
        (None, _state(middle=True), GestureType.NONE, GestureSource.GEOMETRY),
        (None, _state(ring=True), GestureType.NONE, GestureSource.GEOMETRY),
        (
            None,
            _state(index=True, middle=True, ring=True, pinky=True),
            GestureType.PALM,
            GestureSource.GEOMETRY,
        ),
        ("Thumb_Down", _state(thumb=True), GestureType.NONE, GestureSource.GEOMETRY),
        (None, _state(thumb=True, index=True), GestureType.NONE, GestureSource.GEOMETRY),
    ],
)
def test_canned_geometry_collisions(
    raw_label: str | None,
    finger_state: FingerStateResult,
    expected_type: GestureType,
    expected_source: GestureSource,
) -> None:
    mapped = GestureMapper().map(
        raw_label=raw_label,
        raw_confidence=0.9 if raw_label is not None else 0.0,
        finger_state_result=finger_state,
    )

    assert mapped.type is expected_type
    assert mapped.source is expected_source
