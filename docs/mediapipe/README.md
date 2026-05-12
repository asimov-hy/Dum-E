# MediaPipe Notes

Design notes specific to MediaPipe gesture recognition belong here.

Current MediaPipeline phase docs live in `docs/mediapipeline/`.

Current MediaPipe paths:
- Model checksum: `data/mediapipe/models/gesture_recognizer.task.sha256`
- Local model artifact: `data/mediapipe/models/gesture_recognizer.task`
- Regression media manifest:
  `data/mediapipe/regression_media/manifest.json`
- Scripts: `scripts/mediapipe/`
- Local diagnostics: `data/mediapipe/diagnostics/`

Boundary rule:
- MediaPipe code must not directly depend on manual-reading or LeRobot code.
  Keep camera/perception boundaries in `docs/TECHNICAL.md` intact.
