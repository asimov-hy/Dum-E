"""Phase 4 gesture demo with filter-state debug output."""

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
            try:
                frame = source.get_frame()
            except EOFError:
                print("End of source stream.")
                break
            validate_frame(frame)

            started_at = time.perf_counter()
            observations = gesture.analyze_frame(frame)
            events = gesture.events_from_observations(frame, observations)
            filter_debug = gesture.last_filter_debug
            latency_ms = (time.perf_counter() - started_at) * 1000

            _log_frame(
                observations=observations,
                events=events,
                filter_debug=filter_debug,
                latency_ms=latency_ms,
                log_observations=args.log_observations,
                log_events=args.log_events,
                log_filter_state=args.draw_filter_state,
            )

            if cv2 is not None:
                display_rgb = frame.rgb
                if args.show_flipped_display:
                    display_rgb = np.ascontiguousarray(display_rgb[:, ::-1, :])
                bgr = np.ascontiguousarray(display_rgb[:, :, ::-1])
                draw_overlay(
                    bgr,
                    observations,
                    events,
                    cv2_module=cv2,
                    draw_landmarks=args.draw_landmarks,
                    draw_finger_state=args.draw_finger_state,
                    draw_filter_state=args.draw_filter_state,
                    filter_debug=filter_debug,
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
    draw_finger_state: bool = True,
    draw_filter_state: bool = False,
    filter_debug: dict[str, object] | None = None,
) -> np.ndarray:
    """Draw overlay without assuming finger-state data exists."""

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
        if draw_filter_state and filter_debug is not None:
            y += 24
            y = _draw_filter_debug(frame_bgr, y, filter_debug, cv2_module)
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
        if draw_finger_state:
            for finger_text in _finger_state_lines(observation):
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
        y += 24

    if draw_filter_state and filter_debug is not None:
        _draw_filter_debug(frame_bgr, y, filter_debug, cv2_module)

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
    parser = argparse.ArgumentParser(description="DUM-E Phase 4 gesture demo")
    parser.add_argument(
        "--source",
        default="webcam",
        help="fake, webcam, opencv, realsense, or video:<path>",
    )
    parser.add_argument("--frames", type=int, default=None, help="optional frame limit")
    parser.add_argument("--width", type=int, default=None, help="requested source width")
    parser.add_argument("--height", type=int, default=None, help="requested source height")
    parser.add_argument("--device", default="0", help="OpenCV device index or path")
    parser.add_argument("--model-path", default="data/models/gesture_recognizer.task")
    parser.add_argument("--draw-landmarks", action="store_true")
    parser.add_argument("--draw-finger-state", action="store_true")
    parser.add_argument("--draw-filter-state", action="store_true")
    parser.add_argument(
        "--show-flipped-display",
        type=_parse_bool,
        default=False,
        metavar="true|false",
        help="mirror only the displayed frame; inference always uses the original frame",
    )
    parser.add_argument("--log-observations", action="store_true")
    parser.add_argument("--log-events", action="store_true")
    parser.add_argument("--no-display", action="store_true", help="run without cv2.imshow")
    return parser.parse_args()


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


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
    filter_debug: dict[str, object],
    latency_ms: float,
    log_observations: bool,
    log_events: bool,
    log_filter_state: bool,
) -> None:
    print(f"latency_ms={latency_ms:.2f}")
    if log_observations:
        for obs in observations:
            finger_state = _finger_state_log(obs)
            print(
                "observation "
                f"type={obs.type.name} source={obs.source.name} "
                f"raw_label={obs.raw_label} raw_confidence={obs.raw_label_confidence} "
                f"handedness={obs.handedness} hand_index={obs.hand_index} "
                f"{finger_state}"
            )
    if log_events:
        for event in events:
            print(
                "event "
                f"type={event.type.name} source={event.source.name} "
                f"confidence={event.confidence} hand_index={event.hand_index}"
            )
    if log_filter_state:
        print("filter " + " ".join(_filter_debug_lines(filter_debug)))


def _finger_state_lines(observation: GestureObservation) -> list[str]:
    if observation.finger_state_result is None or observation.finger_state is None:
        return ["finger state: not available"]

    state = observation.finger_state
    lines = [
        "fingers "
        f"T={int(state.thumb)} I={int(state.index)} M={int(state.middle)} "
        f"R={int(state.ring)} P={int(state.pinky)} count={observation.finger_count}"
    ]
    if observation.finger_state_result.margins:
        margins = observation.finger_state_result.margins
        lines.append(
            "margins "
            f"T={margins['thumb']:.3f} I={margins['index']:.3f} "
            f"M={margins['middle']:.3f} R={margins['ring']:.3f} "
            f"P={margins['pinky']:.3f}"
        )
    return lines


def _finger_state_log(observation: GestureObservation) -> str:
    if observation.finger_state_result is None or observation.finger_state is None:
        return "finger_state=not_available"

    state = observation.finger_state
    return (
        "finger_state="
        f"thumb={state.thumb},index={state.index},middle={state.middle},"
        f"ring={state.ring},pinky={state.pinky} "
        f"finger_count={observation.finger_count} "
        f"margins={observation.finger_state_result.margins}"
    )


def _draw_filter_debug(
    frame_bgr: np.ndarray,
    y: int,
    filter_debug: dict[str, object],
    cv2_module: Any,
) -> int:
    for line in _filter_debug_lines(filter_debug):
        cv2_module.putText(
            frame_bgr,
            line,
            (12, y),
            cv2_module.FONT_HERSHEY_SIMPLEX,
            0.48,
            (220, 200, 120),
            1,
        )
        y += 22
    return y


def _filter_debug_lines(filter_debug: dict[str, object]) -> list[str]:
    stability_counts = filter_debug.get("stability_counts", {})
    stability_required = filter_debug.get("stability_required_frames", "?")
    return [
        "confidence "
        f"pass={filter_debug.get('confidence_pass_count', 0)} "
        f"drop={filter_debug.get('confidence_drop_count', 0)}",
        f"none_drop={filter_debug.get('none_drop_count', 0)}",
        "stability "
        f"pass={filter_debug.get('stability_pass_count', 0)} "
        f"counts={stability_counts}/{stability_required}",
        "cooldown "
        f"pass={filter_debug.get('cooldown_pass_count', 0)} "
        f"drop={filter_debug.get('cooldown_drop_count', 0)}",
        f"emitted={filter_debug.get('emitted_count', 0)}",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
