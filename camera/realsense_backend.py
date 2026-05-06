"""Intel RealSense camera source with lazy ``pyrealsense2`` import."""

from __future__ import annotations

import importlib
import time
from typing import Any

import numpy as np

from core.frame import Frame, validate_frame


class RealSenseFrameSource:
    """FrameSource implementation for RealSense color and depth streams."""

    def __init__(
        self,
        *,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        camera_name: str = "realsense",
        enable_depth: bool = True,
        timeout_ms: int = 5_000,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.camera_name = camera_name
        self.enable_depth = enable_depth
        self.timeout_ms = timeout_ms
        self.actual_width: int | None = None
        self.actual_height: int | None = None
        self._pipeline: Any | None = None
        self._depth_scale = 0.001
        self._next_frame_id = 0
        self._last_timestamp_ms = -1

    def start(self) -> None:
        if self._pipeline is not None:
            return

        try:
            rs = importlib.import_module("pyrealsense2")
        except ImportError as exc:
            raise RuntimeError(
                "RealSenseFrameSource requires pyrealsense2. Install the "
                "RealSense SDK Python bindings or use backend='fake'/'webcam'."
            ) from exc

        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        if self.enable_depth:
            config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)

        started = False
        try:
            profile = pipeline.start(config)
            started = True
            if self.enable_depth:
                sensor = profile.get_device().first_depth_sensor()
                self._depth_scale = float(sensor.get_depth_scale())
        except Exception as exc:
            if started:
                pipeline.stop()
            raise RuntimeError("Could not start RealSense camera pipeline") from exc

        self._pipeline = pipeline
        self._next_frame_id = 0
        self._last_timestamp_ms = -1

    def stop(self) -> None:
        if self._pipeline is None:
            return

        self._pipeline.stop()
        self._pipeline = None

    def get_frame(self) -> Frame:
        if self._pipeline is None:
            raise RuntimeError("RealSenseFrameSource.start() must be called before get_frame()")

        frames = self._pipeline.wait_for_frames(self.timeout_ms)
        color_frame = frames.get_color_frame()
        if not color_frame:
            raise RuntimeError("RealSense pipeline did not return a color frame")

        color_bgr = np.asanyarray(color_frame.get_data())
        rgb = np.ascontiguousarray(color_bgr[:, :, ::-1], dtype=np.uint8)
        self.actual_height, self.actual_width = rgb.shape[:2]

        depth_m = None
        if self.enable_depth:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_raw = np.asanyarray(depth_frame.get_data())
                depth_m = np.ascontiguousarray(depth_raw.astype(np.float32) * self._depth_scale)

        frame = Frame(
            rgb=rgb,
            timestamp_ms=self._next_timestamp_ms(),
            frame_id=self._next_frame_id,
            depth_m=depth_m,
            camera_name=self.camera_name,
        )
        validate_frame(frame)

        self._next_frame_id += 1
        return frame

    def __enter__(self) -> "RealSenseFrameSource":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()

    def _next_timestamp_ms(self) -> int:
        timestamp_ms = time.monotonic_ns() // 1_000_000
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms
