import numpy as np
import pytest

from camera.source import FakeSource, create_source
from core.frame import Frame, validate_frame


def test_fake_source_returns_valid_frame() -> None:
    source = FakeSource(width=16, height=12)
    source.start()

    try:
        frame = source.get_frame()
    finally:
        source.stop()

    assert isinstance(frame, Frame)
    validate_frame(frame)
    assert frame.rgb.dtype == np.uint8
    assert frame.rgb.ndim == 3
    assert frame.rgb.shape == (12, 16, 3)
    assert frame.rgb.flags["C_CONTIGUOUS"]
    assert frame.camera_name == "fake"


def test_fake_source_timestamps_and_frame_ids_increase() -> None:
    source = FakeSource(width=4, height=3, start_timestamp_ms=100, timestamp_step_ms=5)
    source.start()

    try:
        frames = [source.get_frame() for _ in range(4)]
    finally:
        source.stop()

    assert [frame.timestamp_ms for frame in frames] == [105, 110, 115, 120]
    assert [frame.frame_id for frame in frames] == [0, 1, 2, 3]


def test_fake_source_context_manager_starts_and_stops() -> None:
    source = FakeSource(width=4, height=3)

    assert not source.is_running
    with source as running_source:
        assert running_source is source
        assert source.is_running
        validate_frame(source.get_frame())

    assert not source.is_running
    assert source.start_count == 1
    assert source.stop_count == 1


def test_create_source_fake_returns_usable_frame_source() -> None:
    source = create_source("fake", width=5, height=7)
    source.start()

    try:
        frame = source.get_frame()
    finally:
        source.stop()

    validate_frame(frame)
    assert frame.rgb.shape == (7, 5, 3)
    assert frame.frame_id == 0


def test_fake_source_reuses_prebuilt_frames_with_new_timing() -> None:
    prebuilt = Frame(
        rgb=np.ones((3, 4, 3), dtype=np.uint8) * 127,
        timestamp_ms=999,
        frame_id=999,
        camera_name="prebuilt",
    )
    source = FakeSource(frames=[prebuilt], camera_name="fake-prebuilt")

    with source:
        frame = source.get_frame()

    validate_frame(frame)
    assert frame.timestamp_ms == 33
    assert frame.frame_id == 0
    assert frame.camera_name == "fake-prebuilt"
    assert np.array_equal(frame.rgb, prebuilt.rgb)


def test_fake_source_requires_start_before_get_frame() -> None:
    source = FakeSource()

    with pytest.raises(RuntimeError, match="start"):
        source.get_frame()
