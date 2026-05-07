from perception.mapper import GestureMapper
from perception.types import (
    FingerState,
    FingerStateResult,
    GestureConfig,
    GestureSource,
    GestureType,
    MappedGesture,
)


def test_mapper_accepts_optional_finger_state_and_returns_mapped_gesture() -> None:
    mapped = GestureMapper().map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=_result(index=True),
    )

    assert isinstance(mapped, MappedGesture)


def test_geometry_confidence_uses_finger_state_result_confidence() -> None:
    mapped = GestureMapper().map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=_result(index=True, confidence=0.77),
    )

    assert mapped.confidence == 0.77


def test_geometry_confidence_falls_back_to_config_default() -> None:
    mapped = GestureMapper(GestureConfig(default_geometry_confidence=0.42)).map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=_result(index=True, confidence=None),
    )

    assert mapped.confidence == 0.42


def test_index_only_maps_to_one_finger() -> None:
    mapped = _map(_result(index=True))

    assert mapped.type is GestureType.ONE_FINGER
    assert mapped.source is GestureSource.GEOMETRY


def test_index_middle_maps_to_two_fingers() -> None:
    mapped = _map(_result(index=True, middle=True))

    assert mapped.type is GestureType.TWO_FINGERS
    assert mapped.source is GestureSource.GEOMETRY


def test_index_middle_ring_maps_to_three_fingers() -> None:
    mapped = _map(_result(index=True, middle=True, ring=True))

    assert mapped.type is GestureType.THREE_FINGERS
    assert mapped.source is GestureSource.GEOMETRY


def test_middle_only_maps_to_none() -> None:
    assert _map(_result(middle=True)).type is GestureType.NONE


def test_ring_only_maps_to_none() -> None:
    assert _map(_result(ring=True)).type is GestureType.NONE


def test_thumb_index_maps_to_none() -> None:
    assert _map(_result(thumb=True, index=True)).type is GestureType.NONE


def test_four_fingers_with_thumb_folded_maps_to_palm_when_enabled() -> None:
    mapped = _map(_result(index=True, middle=True, ring=True, pinky=True))

    assert mapped.type is GestureType.PALM
    assert mapped.source is GestureSource.GEOMETRY


def test_all_false_maps_to_fist_when_enabled() -> None:
    mapped = _map(_result())

    assert mapped.type is GestureType.FIST
    assert mapped.source is GestureSource.GEOMETRY


def test_geometry_palm_fallback_can_be_disabled() -> None:
    mapper = GestureMapper(GestureConfig(allow_geometry_palm=False))
    mapped = mapper.map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=_result(index=True, middle=True, ring=True, pinky=True),
    )

    assert mapped.type is GestureType.NONE


def test_geometry_fist_fallback_can_be_disabled() -> None:
    mapper = GestureMapper(GestureConfig(allow_geometry_fist=False))
    mapped = mapper.map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=_result(),
    )

    assert mapped.type is GestureType.NONE


def _map(result: FingerStateResult) -> MappedGesture:
    return GestureMapper().map(
        raw_label=None,
        raw_confidence=0.0,
        finger_state_result=result,
    )


def _result(
    *,
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    confidence: float | None = 0.8,
) -> FingerStateResult:
    return FingerStateResult(
        state=FingerState(
            thumb=thumb,
            index=index,
            middle=middle,
            ring=ring,
            pinky=pinky,
        ),
        confidence=confidence,
        margins=None,
    )
