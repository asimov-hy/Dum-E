"""Phase 2 gesture demo with MediaPipe canned labels."""

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
from core.frame import validate_frame  # noqa: E402
from core.landmarks import Landmark2D  # noqa: E402
from perception.gesture import GestureService  # noqa: E402
from perception.types import GestureEvent, GestureObservation, GestureServiceConfig  # noqa: E402


HAND_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


def main() -> int:
    args = _parse_args()
    cv2 = None if args.no_display else _load_cv2_for_display()
    source = create_source(args.source, **_source_kwargs(args))
    gesture = GestureService(GestureServiceConfig(model_path=args.model_path))

    captured = 0
    try:
        source.start()
        while args.frames is None or captured < args.frames:
            frame = source.get_frame()
            validate_frame(frame)

            started_at = time.perf_counter()
            observations = gesture.analyze_frame(frame)
            events = gesture.events_from_observations(frame, observations)
            latency_ms = (time.perf_counter() - started_at) * 1000

            _log_frame(
                observations=observations,
                events=events,
                latency_ms=latency_ms,
                log_observations=args.log_observations,
                log_events=args.log_events,
            )

            if cv2 is not None:
                bgr = np.ascontiguousarray(frame.rgb[:, :, ::-1])
                draw_overlay(
                    bgr,
                    observations,
                    events,
                    cv2_module=cv2,
                    draw_landmarks=args.draw_landmarks,
                )
                cv2.imshow("DUM-E gesture demo", bgr)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            captured += 1
    except KeyboardInterrupt:
        print("Interrupted; closing gesture demo.")
    finally:
        gesture.close()
        source.stop()
        if cv2 is not None:
            cv2.destroyAllWindows()

    return 0


def draw_overlay(
    frame_bgr: np.ndarray,
    observations: list[GestureObservation],
    events: list[GestureEvent],
    *,
    cv2_module: Any | None,
    draw_landmarks: bool = True,
) -> np.ndarray:
    """Draw Phase 2 overlay without assuming finger-state data exists."""

    if cv2_module is None:
        return frame_bgr

    y = 24
    if not observations:
        cv2_module.putText(
            frame_bgr,
            "no hand",
            (12, y),
            cv2_module.FONT_HERSHEY_SIMPLEX,
            0.6,
            (220, 220, 220),
            2,
        )
        return frame_bgr

    for observation in observations:
        if draw_landmarks and observation.landmarks is not None:
            _draw_hand_skeleton(frame_bgr, observation.landmarks, cv2_module)

        raw_label = observation.raw_label or "None"
        text = (
            f"raw={raw_label} mapped={observation.type.name} "
            f"source={observation.source.name}"
        )
        cv2_module.putText(
            frame_bgr,
            text,
            (12, y),
            cv2_module.FONT_HERSHEY_SIMPLEX,
            0.55,
            (80, 255, 160),
            2,
        )
        y += 24
        finger_text = "finger state: not available"
        cv2_module.putText(
            frame_bgr,
            finger_text,
            (12, y),
            cv2_module.FONT_HERSHEY_SIMPLEX,
            0.5,
            (180, 180, 180),
            1,
        )
        y += 24

    if events:
        event_names = ", ".join(event.type.name for event in events)
        cv2_module.putText(
            frame_bgr,
            f"events={event_names}",
            (12, y),
            cv2_module.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 220, 80),
            2,
        )

    return frame_bgr


def _draw_hand_skeleton(
    frame_bgr: np.ndarray,
    landmarks: tuple[Landmark2D, ...],
    cv2_module: Any,
) -> None:
    height, width = frame_bgr.shape[:2]
    points = [
        (
            int(max(0.0, min(1.0, landmark.x)) * (width - 1)),
            int(max(0.0, min(1.0, landmark.y)) * (height - 1)),
        )
        for landmark in landmarks
    ]

    for start, end in HAND_CONNECTIONS:
        if start < len(points) and end < len(points):
            cv2_module.line(frame_bgr, points[start], points[end], (255, 180, 60), 2)
    for point in points:
        cv2_module.circle(frame_bgr, point, 3, (40, 220, 255), -1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DUM-E Phase 2 gesture demo")
    parser.add_argument("--source", default="webcam", help="fake, webcam, opencv, or realsense")
    parser.add_argument("--frames", type=int, default=None, help="optional frame limit")
    parser.add_argument("--width", type=int, default=None, help="requested source width")
    parser.add_argument("--height", type=int, default=None, help="requested source height")
    parser.add_argument("--device", default="0", help="OpenCV device index or path")
    parser.add_argument("--model-path", default="data/models/gesture_recognizer.task")
    parser.add_argument("--draw-landmarks", action="store_true")
    parser.add_argument("--log-observations", action="store_true")
    parser.add_argument("--log-events", action="store_true")
    parser.add_argument("--no-display", action="store_true", help="run without cv2.imshow")
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
        print("OpenCV is unavailable; running without display.")
        return None


def _log_frame(
    *,
    observations: list[GestureObservation],
    events: list[GestureEvent],
    latency_ms: float,
    log_observations: bool,
    log_events: bool,
) -> None:
    print(f"latency_ms={latency_ms:.2f}")
    if log_observations:
        for obs in observations:
            print(
                "observation "
                f"type={obs.type.name} source={obs.source.name} "
                f"raw_label={obs.raw_label} raw_confidence={obs.raw_label_confidence} "
                f"handedness={obs.handedness} hand_index={obs.hand_index}"
            )
    if log_events:
        for event in events:
            print(
                "event "
                f"type={event.type.name} source={event.source.name} "
                f"confidence={event.confidence} hand_index={event.hand_index}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
