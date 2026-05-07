from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import numpy as np

from camera.opencv_backend import OpenCVFrameSource
from camera.realsense_backend import RealSenseFrameSource


def test_opencv_source_converts_bgr_to_rgb_before_frame(
    monkeypatch,
) -> None:
    bgr = np.array([[[10, 20, 30], [1, 2, 3]]], dtype=np.uint8)
    fake_cv2 = ModuleType("cv2")
    fake_cv2.CAP_PROP_FRAME_WIDTH = 3
    fake_cv2.CAP_PROP_FRAME_HEIGHT = 4
    fake_cv2.COLOR_BGR2RGB = 5
    fake_cv2.VideoCapture = lambda device: _FakeOpenCVCapture(bgr)

    def cvt_color(image: np.ndarray, code: int) -> np.ndarray:
        assert code == fake_cv2.COLOR_BGR2RGB
        return image[:, :, ::-1]

    fake_cv2.cvtColor = cvt_color
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    source = OpenCVFrameSource(device=0, camera_name="opencv-test")
    source.start()
    try:
        frame = source.get_frame()
    finally:
        source.stop()

    assert np.array_equal(frame.rgb, np.array([[[30, 20, 10], [3, 2, 1]]], dtype=np.uint8))
    assert frame.rgb.flags["C_CONTIGUOUS"]
    assert frame.rgb.dtype == np.uint8
    assert frame.camera_name == "opencv-test"


def test_realsense_source_requests_bgr8_color_stream(
    monkeypatch,
) -> None:
    captured_streams: list[tuple[object, ...]] = []
    fake_rs = ModuleType("pyrealsense2")
    fake_rs.stream = SimpleNamespace(color="color", depth="depth")
    fake_rs.format = SimpleNamespace(bgr8="bgr8", z16="z16")
    fake_rs.config = lambda: _FakeRealSenseConfig(captured_streams)
    fake_rs.pipeline = _FakeRealSensePipeline
    monkeypatch.setitem(sys.modules, "pyrealsense2", fake_rs)

    source = RealSenseFrameSource(width=320, height=240, fps=15, enable_depth=False)
    source.start()
    try:
        assert captured_streams == [("color", 320, 240, "bgr8", 15)]
    finally:
        source.stop()


def test_realsense_source_converts_bgr_to_rgb_before_frame() -> None:
    bgr = np.array([[[7, 8, 9], [40, 50, 60]]], dtype=np.uint8)
    source = RealSenseFrameSource(enable_depth=False, camera_name="realsense-test")
    source._pipeline = _FakeRealSenseFramePipeline(bgr)

    frame = source.get_frame()

    assert np.array_equal(frame.rgb, np.array([[[9, 8, 7], [60, 50, 40]]], dtype=np.uint8))
    assert frame.rgb.flags["C_CONTIGUOUS"]
    assert frame.rgb.dtype == np.uint8
    assert frame.camera_name == "realsense-test"


class _FakeOpenCVCapture:
    def __init__(self, bgr: np.ndarray) -> None:
        self._bgr = bgr
        self.released = False

    def set(self, prop: int, value: int) -> None:
        del prop, value

    def get(self, prop: int) -> int:
        del prop
        return 1

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        return True, self._bgr

    def release(self) -> None:
        self.released = True


class _FakeRealSenseConfig:
    def __init__(self, captured_streams: list[tuple[object, ...]]) -> None:
        self._captured_streams = captured_streams

    def enable_stream(self, *args: object) -> None:
        self._captured_streams.append(args)


class _FakeRealSensePipeline:
    def start(self, config: _FakeRealSenseConfig) -> object:
        del config
        return SimpleNamespace()

    def stop(self) -> None:
        pass


class _FakeRealSenseFramePipeline:
    def __init__(self, bgr: np.ndarray) -> None:
        self._bgr = bgr

    def wait_for_frames(self, timeout_ms: int) -> object:
        del timeout_ms
        return _FakeRealSenseFrames(self._bgr)


class _FakeRealSenseFrames:
    def __init__(self, bgr: np.ndarray) -> None:
        self._bgr = bgr

    def get_color_frame(self) -> object:
        return _FakeRealSenseColorFrame(self._bgr)


class _FakeRealSenseColorFrame:
    def __init__(self, bgr: np.ndarray) -> None:
        self._bgr = bgr

    def get_data(self) -> np.ndarray:
        return self._bgr
