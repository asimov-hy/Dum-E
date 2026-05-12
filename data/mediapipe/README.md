# MediaPipe Data

MediaPipe artifacts live here without coupling to manual-reading or LeRobot data.

- `models/`: local model artifacts and tracked checksums.
- `regression_media/`: recorded media manifest and real regression clips.
- `diagnostics/`: local diagnostic outputs; generated contents are ignored.

Tracking policy:
- Track `models/gesture_recognizer.task.sha256`.
- Keep `models/gesture_recognizer.task` local/external; it is ignored by
  `.gitignore`.
- Track `regression_media/manifest.json` and `regression_media/README.md`.
- Do not add fake regression clips or mark missing clips present.
