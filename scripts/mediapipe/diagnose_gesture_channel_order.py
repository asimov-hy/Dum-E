# scripts/mediapipe/diagnose_gesture_channel_order.py

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow running from repo root without manually setting PYTHONPATH.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from perception.gesture import GestureService  # noqa: E402
from perception.types import GestureServiceConfig  # noqa: E402


def analyze_raw(
    service: GestureService,
    image: np.ndarray,
    *,
    timestamp_ms: int,
) -> str:
    # Diagnostic only: directly inspect MediaPipe output before mapper/filtering.
    # The AS_IS path intentionally may not satisfy Frame.rgb's RGB contract, so
    # feed MediaPipe directly instead of constructing an invalid Frame.
    mp_image = service._runtime.image_cls(
        image_format=service._runtime.image_format,
        data=np.ascontiguousarray(image, dtype=np.uint8),
    )

    result = service._runtime.recognizer.recognize_for_video(
        mp_image,
        timestamp_ms,
    )

    hand_landmarks = getattr(result, "hand_landmarks", None) or []
    gestures = getattr(result, "gestures", None) or []
    handednesses = getattr(result, "handedness", None) or []

    if not hand_landmarks:
        return "NO_HAND"

    parts: list[str] = []

    for hand_index, landmarks in enumerate(hand_landmarks):
        categories = []
        if hand_index < len(gestures):
            categories = [
                (
                    getattr(category, "category_name", None),
                    round(float(getattr(category, "score", 0.0)), 3),
                )
                for category in gestures[hand_index]
            ]

        handedness = None
        if hand_index < len(handednesses) and handednesses[hand_index]:
            handedness = getattr(
                handednesses[hand_index][0],
                "category_name",
                None,
            )

        xs = [float(lm.x) for lm in landmarks]
        ys = [float(lm.y) for lm in landmarks]

        bbox_w = max(xs) - min(xs)
        bbox_h = max(ys) - min(ys)

        top = categories[0] if categories else None

        parts.append(
            f"hand={hand_index} "
            f"handedness={handedness!r} "
            f"bbox=({bbox_w:.3f}x{bbox_h:.3f}) "
            f"top={top} "
            f"categories={categories}"
        )

    return " | ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to gesture_recognizer.task")
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--mjpg", action="store_true")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera_index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    if args.mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera_index}")

    config = GestureServiceConfig(model_path=args.model)

    service_as_is = GestureService(config)
    service_bgr2rgb = GestureService(config)

    frame_id = 0
    timestamp_ms = 0

    print("Show each test gesture clearly: open palm, closed fist, thumbs up.")
    print("Compare AS_IS vs BGR2RGB.")
    print("Press q to quit.")

    try:
        while True:
            ok, image = cap.read()
            if not ok:
                print("Failed to read frame")
                continue

            frame_id += 1
            timestamp_ms += int(1000 / args.fps)

            # Path A: camera image passed directly to MediaPipe as-is.
            as_is = image

            # Path B: OpenCV BGR converted to true RGB before MediaPipe input.
            bgr2rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            result_as_is = analyze_raw(
                service_as_is,
                as_is,
                timestamp_ms=timestamp_ms,
            )

            result_bgr2rgb = analyze_raw(
                service_bgr2rgb,
                bgr2rgb,
                timestamp_ms=timestamp_ms,
            )

            if frame_id % 10 == 0:
                print()
                print(f"frame={frame_id}")
                print("AS_IS  :", result_as_is)
                print("BGR2RGB:", result_bgr2rgb)

            cv2.imshow("camera raw shown by OpenCV", image)

            # This should look visually identical to the raw OpenCV window
            # if bgr2rgb is truly RGB being converted back for display.
            cv2.imshow(
                "BGR2RGB path shown by OpenCV",
                cv2.cvtColor(bgr2rgb, cv2.COLOR_RGB2BGR),
            )

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    finally:
        service_as_is.close()
        service_bgr2rgb.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
