import pytest

from perception.mapper import GestureMapper
from perception.types import GestureSource, GestureType


@pytest.mark.parametrize(
    ("raw_label", "expected_type"),
    [
        ("Thumb_Up", GestureType.THUMBS_UP),
        ("Open_Palm", GestureType.PALM),
        ("Closed_Fist", GestureType.FIST),
        ("Victory", GestureType.NONE),
        ("Pointing_Up", GestureType.NONE),
        ("Thumb_Down", GestureType.NONE),
        ("Surprise_Label", GestureType.NONE),
        (None, GestureType.NONE),
    ],
)
def test_phase2_canned_mapper(raw_label: str | None, expected_type: GestureType) -> None:
    mapped = GestureMapper().map(raw_label=raw_label, raw_confidence=0.8)

    assert mapped.type is expected_type
    assert mapped.source is GestureSource.CANNED


def test_none_raw_label_uses_zero_confidence_when_confidence_is_absent() -> None:
    mapped = GestureMapper().map(raw_label=None, raw_confidence=None)

    assert mapped.type is GestureType.NONE
    assert mapped.confidence == 0.0
