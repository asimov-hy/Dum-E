# Known Issues

## RealSense/ABKO MediaPipe canned palm/fist reliability

Status: Temporary mitigation in place

Affected cameras:
- RealSense via USB/OpenCV
- ABKO USB camera

Working camera:
- Embedded/webcam path

Root cause observed:
- OpenCV frames are BGR and must be converted to RGB before `Frame(rgb=...)`.
- After conversion, RealSense/ABKO detect hands but MediaPipe often returns
  `raw_label="None"` for `Open_Palm` and `Closed_Fist`.

Current mitigation:
- BGR -> RGB conversion is done in camera adapters before creating `Frame(rgb=...)`.
- A landmark fallback classifies `Open_Palm` and `Closed_Fist` when the MediaPipe canned
  label is missing or `"None"`.
- Fallback observations and events are tagged as `GestureSource.GEOMETRY` with confidence
  `0.60`.

Known risks:
- The simple y-coordinate heuristic may misclassify angled hands.
- A thumbs-up with a missing canned label may look like a fist.
- Stability and cooldown filters exist, but they do not prove camera-specific
  RealSense/ABKO reliability without hardware validation.
- Manual webcam and RealSense validation is still required unless recorded in
  the phase checklist.

Follow-up work:
- Test RealSense/ABKO physically.
- Compare saved camera frames across working and affected camera paths.
- Tune exposure, resolution, and focus.
- Consider the `pyrealsense2` color stream instead of `/dev/videoX`.
- Add thumb-aware geometry.
- Tune temporal filter thresholds against recorded clips.
- Use `scripts/mediapipe/diagnose_gesture_channel_order.py` for channel-order
  and raw-label comparison when camera behavior differs.
- Store recorded clips under `data/mediapipe/regression_media/` and keep
  MediaPipe diagnostic outputs under `data/mediapipe/diagnostics/`.
- Track validation status in `docs/mediapipeline/phase_verification_checklist.md`.
