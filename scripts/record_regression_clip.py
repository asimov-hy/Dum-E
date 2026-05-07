"""Record future DUM-E regression clips from a FrameSource.

The script records the raw RGB FrameSource stream. It converts RGB to BGR only
at the OpenCV video-writing/display boundary and never flips frames before
recording.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def main() -> int:
    args = parse_args()
    try:
        record_clip(args)
    except KeyboardInterrupt:
        print("Interrupted; closing recording.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a DUM-E regression clip")
    parser.add_argument("--source", default="webcam", help="webcam, realsense, or another FrameSource backend")
    parser.add_argument("--output", required=True, help="output .mp4 path")
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--expected", required=True, help="GestureType name or NONE")
    parser.add_argument("--suite", default="primary", help="primary, webcam, realsense_rgb, or custom")
    parser.add_argument("--camera-backend", default=None, help="webcam, realsense, or custom backend label")
    parser.add_argument("--camera-model", default=None)
    parser.add_argument("--resolution", default=None, help="for example 640x480")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--duration-seconds", type=float, default=5.0)
    parser.add_argument("--notes", default="")
    parser.add_argument("--preview", action="store_true", help="show a display preview while recording")
    parser.add_argument(
        "--show-flipped-display",
        type=_parse_bool,
        default=False,
        metavar="true|false",
        help="mirror preview only; recorded/inference frames are not flipped",
    )
    return parser.parse_args(argv)


def record_clip(args: argparse.Namespace) -> None:
    if args.duration_seconds <= 0:
        raise ValueError("--duration-seconds must be positive")
    if args.fps <= 0:
        raise ValueError("--fps must be positive")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2 = importlib.import_module("cv2")
    create_source, validate_frame = _load_frame_tools()
    source = create_source(args.source, **_source_kwargs(args))
    writer: Any | None = None
    frame_count = 0
    started_at = time.monotonic()

    try:
        source.start()
        while time.monotonic() - started_at < args.duration_seconds:
            frame = source.get_frame()
            validate_frame(frame)
            if writer is None:
                height, width = frame.rgb.shape[:2]
                writer = _create_writer(cv2, output_path, args.fps, width, height)

            writer.write(np.ascontiguousarray(frame.rgb[:, :, ::-1]))
            frame_count += 1

            if args.preview:
                display_rgb = frame.rgb
                if args.show_flipped_display:
                    display_rgb = np.ascontiguousarray(display_rgb[:, ::-1, :])
                cv2.imshow("DUM-E regression recording", display_rgb[:, :, ::-1])
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except Exception as exc:
        raise RuntimeError(
            "Could not record regression clip. Check camera availability, "
            "OpenCV installation, and source arguments."
        ) from exc
    finally:
        if writer is not None:
            writer.release()
        source.stop()
        if args.preview:
            cv2.destroyAllWindows()

    if frame_count == 0:
        raise RuntimeError("No frames were recorded; clip was not usable")

    metadata = _metadata(args, frame_count=frame_count)
    metadata_path = output_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Recorded {frame_count} frames to {output_path}")
    print(f"Wrote metadata to {metadata_path}")
    print("Suggested manifest entry:")
    print(json.dumps(_suggest_manifest_entry(args, output_path), indent=2, sort_keys=True))


def _load_frame_tools() -> tuple[Any, Any]:
    # Keep --help and import-time scaffold tests free of camera/OpenCV imports.
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_text = str(repo_root)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)

    from camera.source import create_source
    from core.frame import validate_frame

    return create_source, validate_frame


def _source_kwargs(args: argparse.Namespace) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    resolution = _parse_resolution(args.resolution)
    if resolution is not None:
        kwargs["width"], kwargs["height"] = resolution
    if args.source == "realsense":
        kwargs["fps"] = int(args.fps)
    return kwargs


def _create_writer(
    cv2: Any,
    output_path: Path,
    fps: float,
    width: int,
    height: int,
) -> Any:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer for {output_path}")
    return writer


def _metadata(args: argparse.Namespace, *, frame_count: int) -> dict[str, object]:
    return {
        "clip_id": args.clip_id,
        "expected": args.expected,
        "suite": args.suite,
        "source": args.source,
        "camera_backend": args.camera_backend or args.source,
        "camera_model": args.camera_model,
        "resolution": args.resolution,
        "fps": args.fps,
        "frame_count": frame_count,
        "duration_seconds": args.duration_seconds,
        "created_at": datetime.now(UTC).isoformat(),
        "notes": args.notes,
    }


def _suggest_manifest_entry(args: argparse.Namespace, output_path: Path) -> dict[str, object]:
    expected = args.expected.upper()
    return {
        "id": args.clip_id,
        "path": str(output_path),
        "present": True,
        "expected_type": expected,
        "expected": expected,
        "kind": "none" if expected == "NONE" else "target",
        "category": "target" if expected != "NONE" else "none_rejection",
        "required_for_phase5": args.suite == "primary",
        "required_for_acceptance": args.suite == "primary",
        "suite": args.suite,
        "camera_backend": args.camera_backend or args.source,
        "camera_model": args.camera_model,
        "resolution": args.resolution,
        "fps": args.fps,
        "notes": args.notes,
    }


def _parse_resolution(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    normalized = value.lower().strip()
    if "x" not in normalized:
        raise argparse.ArgumentTypeError("--resolution must look like 640x480")
    width_text, height_text = normalized.split("x", 1)
    return int(width_text), int(height_text)


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


if __name__ == "__main__":
    raise SystemExit(main())
