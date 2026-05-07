from __future__ import annotations

import sys
from types import ModuleType

import numpy as np
import pytest

from camera.source import create_source
from camera.video_backend import VideoFileFrameSource


def test_video_file_source_emits_rgb_frames_with_deterministic_timestamps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"not a real video; fake cv2 supplies frames")
    bgr_frames = [
        np.array([[[10, 20, 30]]], dtype=np.uint8),
        np.array([[[1, 2, 3]]], dtype=np.uint8),
    ]
    fake_capture = _FakeVideoCapture(bgr_frames, fps=2.0)
    fake_cv2 = _fake_cv2(fake_capture)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    source = VideoFileFrameSource(path, camera_name="video-test")
    source.start()
    try:
        first = source.get_frame()
        second = source.get_frame()
        with pytest.raises(EOFError):
            source.get_frame()
    finally:
        source.stop()

    assert np.array_equal(first.rgb, np.array([[[30, 20, 10]]], dtype=np.uint8))
    assert np.array_equal(second.rgb, np.array([[[3, 2, 1]]], dtype=np.uint8))
    assert [first.timestamp_ms, second.timestamp_ms] == [0, 500]
    assert [first.frame_id, second.frame_id] == [0, 1]
    assert first.camera_name == "video-test"
    assert fake_capture.released


def test_create_source_supports_video_uri(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"fake")
    fake_capture = _FakeVideoCapture([np.zeros((1, 1, 3), dtype=np.uint8)], fps=30.0)
    monkeypatch.setitem(sys.modules, "cv2", _fake_cv2(fake_capture))

    source = create_source(f"video:{path}")
    source.start()
    try:
        frame = source.get_frame()
    finally:
        source.stop()

    assert frame.frame_id == 0
    assert frame.camera_name == f"video:{path}"


class _FakeVideoCapture:
    def __init__(self, bgr_frames: list[np.ndarray], *, fps: float) -> None:
        self._frames = list(bgr_frames)
        self._fps = fps
        self.released = False

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        del prop
        return self._fps

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._frames:
            return False, None
        return True, self._frames.pop(0)

    def release(self) -> None:
        self.released = True


def _fake_cv2(capture: _FakeVideoCapture) -> ModuleType:
    fake_cv2 = ModuleType("cv2")
    fake_cv2.CAP_PROP_FPS = 5
    fake_cv2.COLOR_BGR2RGB = 7
    fake_cv2.VideoCapture = lambda path: capture

    def cvt_color(image: np.ndarray, code: int) -> np.ndarray:
        assert code == fake_cv2.COLOR_BGR2RGB
        return image[:, :, ::-1]

    fake_cv2.cvtColor = cvt_color
    return fake_cv2
