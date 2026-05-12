# DUM-E Creation Log

This log records current development decisions and progress. Historical plans
that mixed implemented behavior with roadmap items are superseded by the policy
below.

Current canonical RAG/developer state lives in `docs/TECHNICAL.md`. Historical
entries below may describe the project at the time they were written.

## 2026-05-11 - Feature-Lane Repository Organization

### Repository Organization

- Organized manual-reading, MediaPipe/MediaPipeline, and LeRobot work into
  separate data, docs, and script lanes.
- Moved manual reference images to `data/manuals/raw/`.
- Moved MediaPipe model checksum and local model artifact path to
  `data/mediapipe/models/`.
- Moved regression media manifest and README to
  `data/mediapipe/regression_media/`.
- Moved MediaPipe scripts to `scripts/mediapipe/`.
- Moved MediaPipeline docs to `docs/mediapipeline/`.
- Added future-lane placeholders under `docs/manuals/`, `docs/mediapipe/`,
  `docs/lerobot/`, `scripts/manuals/`, and `scripts/lerobot/`.

### Boundary Decision

- Manual-reading, MediaPipe/MediaPipeline, and LeRobot should remain independent
  until a concrete workflow requires a narrow shared interface.
- LeRobot integration code belongs under `src/dume/integrations/lerobot/`.
- `camera/` remains the camera source layer; it lazily delegates
  `backend="lerobot"` to the LeRobot integration placeholder.

### Validation Status

- `python` was not on PATH in the organizing shell.
- `python3 -m pytest`: 159 passed, 21 skipped.
- `python3 -m ruff check .`: passed.
- `python3 scripts/mediapipe/check_regression_media.py`: passed and reported
  21 missing clips, including 19 required Phase 5 clips.
- `git diff --check`: passed.

## 2026-05-03 - Foundation Scaffold Update

### Documentation Policy

- `README.md` lists only commands, packages, and features that exist today.
- Roadmap items are clearly labeled as planned.
- `docs/TECHNICAL.md` is the canonical RAG/agent context and labels modules as
  `Implemented`, `Stub`, or `Planned`.
- Code, docs, and interface contracts should be updated together.

### Dependency Policy

- `pyproject.toml` is the single dependency source.
- `requirements.txt` and `requirements-dev.txt` remain removed for now.
- Optional extras should be added only when real code requires them.
- Do not add `rag` or `ai` extras before corresponding packages, interfaces, or
  dependencies exist.

### Implemented

- Replaced the arm placeholder with `ArmDriver` and `MockArmDriver`.
- Added typed control exceptions in `control/exceptions.py`.
- Replaced the teleop placeholder with `TeleopDriver`, `MockTeleopDriver`, and
  CLI-friendly status text.
- Extended `ReplayService` with `execute_pose()` and `execute_motion()` through
  an injected arm driver.
- Added `WorkspaceConfig`, workspace load/save helpers, and default
  `config/workspace.yaml`.
- Extended `ControlSession` to load, create, save, and summarize workspace
  config.
- Added `dume.logging` helpers and `logs/.gitkeep`.
- Added `data/manuals/processed/.gitkeep` for future manual inputs.
- Rewrote README and TECHNICAL docs around current truth versus roadmap.
- Added tests for control interfaces, workspace config, logging, and README
  command truthfulness.

### Current Staging Decision

- `camera/`, `manual/`, and `autonomy/` packages are not created in this phase.
- Add those packages later only when their first scoped interfaces and tests land
  in the same change.
- Planned subsystem direction remains: future `autonomy/` coordinates future
  `control/`, `camera/`, and `manual/` layers without cross-importing between
  the leaf layers.

### Verification Status

- `pytest -q`: 16 passed.
- `python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- `ruff check src tests`: pending in this shell because `ruff` is not installed.
