"""Camera-only smoke test for Phase 1."""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camera.source import create_source  # noqa: E402
from core.frame import Frame, validate_frame  # noqa: E402


def main() -> int:
    args = _parse_args()
    source = create_source(
        args.source,
        **_source_kwargs(args),
    )
    cv2 = None if args.no_display else _load_cv2_for_display()

    captured = 0
    previous_timestamp_ms: int | None = None
    previous_frame_id: int | None = None
    last_frame: Frame | None = None
    started_at = time.perf_counter()

    try:
        source.start()
        while captured < args.frames:
            frame = source.get_frame()
            validate_frame(frame)
            _assert_strictly_increasing_timestamp(frame, previous_timestamp_ms)
            _assert_strictly_increasing_frame_id(frame, previous_frame_id)

            previous_timestamp_ms = frame.timestamp_ms
            previous_frame_id = frame.frame_id
            last_frame = frame
            captured += 1

            if cv2 is not None:
                bgr = np.ascontiguousarray(frame.rgb[:, :, ::-1])
                cv2.imshow("DUM-E camera smoke", bgr)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        print("Interrupted; releasing camera.")
    finally:
        source.stop()
        if cv2 is not None:
            cv2.destroyAllWindows()

    elapsed = max(time.perf_counter() - started_at, 1e-9)
    _print_summary(captured, elapsed, last_frame)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DUM-E camera smoke test")
    parser.add_argument("--source", default="webcam", help="fake, webcam, opencv, or realsense")
    parser.add_argument("--frames", type=int, default=100, help="number of frames to capture")
    parser.add_argument("--width", type=int, default=None, help="requested frame width")
    parser.add_argument("--height", type=int, default=None, help="requested frame height")
    parser.add_argument("--device", default="0", help="OpenCV camera device index or path")
    parser.add_argument("--no-display", action="store_true", help="capture without cv2.imshow")
    return parser.parse_args()


def _source_kwargs(args: argparse.Namespace) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if args.width is not None:
        kwargs["width"] = args.width
    if args.height is not None:
        kwargs["height"] = args.height
    if args.source.lower() in {"webcam", "opencv"}:
        kwargs["device"] = args.device
    return kwargs


def _load_cv2_for_display() -> Any | None:
    try:
        return importlib.import_module("cv2")
    except ImportError:
        print("OpenCV is unavailable; capture will run without display.")
        return None


def _assert_strictly_increasing_timestamp(
    frame: Frame,
    previous_timestamp_ms: int | None,
) -> None:
    if previous_timestamp_ms is not None and frame.timestamp_ms <= previous_timestamp_ms:
        raise AssertionError(
            "timestamp_ms must increase strictly: "
            f"previous={previous_timestamp_ms}, current={frame.timestamp_ms}"
        )


def _assert_strictly_increasing_frame_id(
    frame: Frame,
    previous_frame_id: int | None,
) -> None:
    if previous_frame_id is None or frame.frame_id is None:
        return
    if frame.frame_id <= previous_frame_id:
        raise AssertionError(
            "frame_id must increase strictly: "
            f"previous={previous_frame_id}, current={frame.frame_id}"
        )


def _print_summary(captured: int, elapsed: float, last_frame: Frame | None) -> None:
    fps = captured / elapsed
    print(f"Captured frames: {captured}")
    print(f"Average FPS: {fps:.2f}")
    if last_frame is None:
        print("No frames captured.")
        return

    print(f"Frame shape: {last_frame.rgb.shape}")
    print(f"Camera name: {last_frame.camera_name}")
    print(f"Depth present: {last_frame.depth_m is not None}")


if __name__ == "__main__":
    raise SystemExit(main())
