# DUM-E Technical Documentation

Purpose: canonical agent/developer RAG guide for DUM-E. Keep this document
accurate enough that a new human, developer, or agent can start from it without
inferring repo state from stale roadmap text.

`README.md` is the concise, human-facing project overview. This document owns
the detailed setup, validation, architecture boundaries, current project status,
and agent rules.

Last updated: 2026-05-07
Current phase: foundation scaffold plus DUM-E MediaPipeline Phase 5
infrastructure. Recorded-media clips are still required before Phase 5 can be
marked PASS.

## Agent Context Rules

- Label every subsystem as `Implemented`, `Stub`, or `Planned`.
- README may list a command or package as current only if it exists in code.
- Update this document in the same change as interface, command, config, or
  architecture changes.
- Conda is the canonical runtime environment for running the full DUM-E program.
- The clean-machine full-program environment is the name declared in
  `environment.yml`, currently `dume`.
- `dume-media` is a specialized MediaPipe/MediaPipeline test environment only;
  do not treat it as the canonical full-program runtime.
- Do not use `base` as a project runtime. Do not treat `lerobot` as the DUM-E
  canonical environment unless the project owner explicitly says so.
- `.venv/` is local-only for editor, test, or agent execution. Do not infer the
  intended project runtime from `.venv/`.
- In an existing workspace, validate with the existing intended conda
  environment. Do not create, update, remove, prune, or otherwise mutate conda
  environments unless the user explicitly asks.
- `pyproject.toml` remains the Python package and dependency metadata source. Do
  not restore requirements files unless a verified consumer needs them.
- Do not add optional extras such as `rag` or `ai` before real code and
  dependencies exist.
- Do not re-audit stable facts already documented here unless relevant files
  changed or the user explicitly asks for a fresh audit.

## Project Identity

| Field | Value |
| --- | --- |
| Name | DUM-E |
| Type | Automatic tool provider foundation |
| Current POC direction | LEGO brick/bin provider |
| Language | Python 3.10+ |
| Packaging | `pyproject.toml` with editable install |
| CLI entrypoint | `dume` -> `src/dume/main.py:app` |
| Hardware target | SO-101 arm with sts3215 servos |
| Camera target | Intel RealSense D435 |

## Current Status

| Subsystem | Status | Notes |
| --- | --- | --- |
| `config.py` | Implemented | Pydantic models and YAML/JSON load/save helpers for hardware, calibration, workspace, poses, and motions. |
| `control/session.py` | Implemented | Loads or creates hardware, calibration, workspace, and pose files. |
| `control/recording.py` | Implemented | Stores poses and motion skeletons with snake_case validation. |
| `control/motors.py` | Implemented | Config-backed motor scan and ID updates; no live bus yet. |
| `control/calibration.py` | Implemented | Calibration metadata sync/read; no guided hardware workflow yet. |
| `control/exceptions.py` | Implemented | Typed control exceptions for driver and motion failures. |
| `control/arm.py` | Stub | `ArmDriver` interface and `MockArmDriver`; real LeRobot driver planned. |
| `control/teleop.py` | Stub | `TeleopDriver`, `MockTeleopDriver`, and CLI status text; live input planned. |
| `control/replay.py` | Implemented | Readable replay plans plus execution through an injected `ArmDriver`. |
| `logging.py` | Implemented | Project logger helper and file logging setup. |
| `core/` | Implemented | MediaPipeline `Frame`, landmarks, and `FrameSource` contracts. |
| `camera/` | Implemented | Fake, OpenCV webcam, RealSense-lazy, LeRobot-placeholder, and video-file frame sources. |
| `perception/` | Implemented | MediaPipe gesture service, canned + geometry mapper, temporal filters, and mock operator-presence boundary. |
| `demos/gesture_demo.py` | Implemented | Webcam/RealSense/video demo with landmarks, finger-state, and filter-state debug overlays. |
| `tests/test_regression_media.py` | Partial | Manifest-driven recorded-media harness exists; required clips are not present yet. |
| `manual/` | Planned | No package yet; manual parsing interfaces come in a later phase. |
| `autonomy/` | Planned | No package yet; state machine scaffolding comes in a later phase. |
| `README.md` | Implemented | Current truth plus roadmap; planned commands are not listed as current. |

## Architecture Rules

Layer direction:

```text
control/ is implemented today
core/ owns MediaPipeline contracts
camera/ may import core/
perception/ may import core/
camera/ and perception/ do not import each other
planned autonomy/ coordinates control/ and perception outputs later
```

Rules:

- Planned `autonomy/` coordinates runtime flow and passes data between subsystems.
- `core/`, `camera/`, and `perception/` stay separated by the MediaPipeline
  contracts.
- Planned `control/` and `manual/` layers must not import from camera/perception
  directly.
- Real hardware/perception/model code enters behind interfaces plus mocks.
- Avoid provider registries until there are at least two real implementations or
  a concrete config-driven switch.

MediaPipeline boundary rules:

- `core/` must not import `camera/` or `perception/`.
- `camera/` may import `core/`, but must not import `perception/`.
- `perception/` may import `core/`, but must not import `camera/`.
- `demos/` may wire camera and perception together for user-facing examples.
- `GestureService` consumes `Frame` objects or core frame-derived data, not
  camera backend objects.
- `GestureEvent` must not emit `GestureType.NONE`.

## Current CLI

Implemented commands:

```bash
dume --project-root . init
dume --project-root . status
dume --project-root . motors scan
dume --project-root . motors set-id --name gripper --to-id 9
dume --project-root . calibrate init
dume --project-root . calibrate show
dume --project-root . teleop
dume --project-root . poses list
dume --project-root . poses save inspection_pose --joints 0,0,0,0,0,0
dume --project-root . motions list
dume --project-root . motions scaffold inspection_cycle --poses home,rack_approach
dume --project-root . replay pose home
dume --project-root . replay motion inspection_cycle
```

Planned commands, not implemented yet: live camera commands, manual image import,
and autonomy `run` commands.

## Interface Contracts

`ArmDriver`:

```python
connect() -> None
disconnect() -> None
move_joints(joints: list[float], speed: float = 0.5) -> bool
read_joints() -> list[float]
is_connected() -> bool
```

`MockArmDriver.move_joints()` and `read_joints()` raise `ConnectionError`
when called before `connect()`. `move_joints()` raises `JointLimitError` for an
empty joint target.

Control exceptions:

```python
HardwareError
ConnectionError
MotorStallError
JointLimitError
CalibrationError
```

`TeleopDriver`:

```python
start() -> None
stop() -> None
is_active() -> bool
```

`ReplayService`:

```python
pose_plan(name: str) -> str
motion_plan(name: str) -> str
execute_pose(name: str, driver: ArmDriver) -> bool
execute_motion(name: str, driver: ArmDriver) -> bool
```

`ControlSession`:

```python
ControlSession.load(root: Path) -> ControlSession
bootstrap() -> None
save_all() -> None
save_hardware() -> None
save_calibration() -> None
save_workspace() -> None
save_poses() -> None
status_summary() -> dict[str, int | str]
```

Important side effect: `ControlSession.load()` creates missing default config and
data files.

`dume.logging`:

```python
get_logger(name: str) -> logging.Logger
setup_file_logging(log_dir: Path, filename: str = "dume.log") -> Path
```

## Data Models

Implemented config models:

```python
SerialConfig
MotorConfig
HardwareConfig
JointCalibration
CalibrationConfig
BinPosition
LoadoutArea
ActorZone
WorkspaceConfig
PoseLibrary
MotionStep
MotionDefinition
ProjectPaths
```

Workspace defaults live in `config/workspace.yaml`:

- Three storage bin positions.
- Loadout capacity of 2.
- Actor zone bounds.
- Empty camera serial placeholder.
- Safety margin of 0.05 meters.

## Dependencies

Runtime policy:

- Conda is the canonical runtime environment for the full DUM-E program.
- `environment.yml` defines the minimal conda environment: Python plus `pip`
  from conda-forge. Its environment name is the clean-machine full-program
  environment name, currently `dume`.
- `dume-media` may exist locally as a specialized MediaPipe/MediaPipeline test
  environment, but it is not the canonical full-program runtime.
- `base` is not a project runtime, and `lerobot` is not the DUM-E canonical
  environment unless the project owner explicitly says so.
- Install the package and Python dependencies from `pyproject.toml` with
  `python -m pip install -e ...` inside the active conda environment.
- `.venv/` may be created for editor, testing, or agent workflows only; it is
  ignored and not canonical.

Current Python package/dependency metadata source: `pyproject.toml`.

Runtime:

```text
pydantic>=2.7
PyYAML>=6.0
```

Development:

```text
pytest>=8.0
numpy
ruff>=0.6
```

Optional extras now include `camera`, `perception`, `realsense`, and `dev`.
Future optional extras should be added only when their code requires them. RAG or
model-provider support remains a roadmap possibility and has no package or
dependency group yet.

## Clean Machine Setup

Canonical conda runtime setup:

```bash
conda env create -f environment.yml
conda activate dume
python -m pip install -e ".[dev,camera,perception]"
```

Optional RealSense hardware dependency:

```bash
python -m pip install -e ".[realsense]"
```

Local-only venv setup is allowed for editor, testing, and agent execution, but
it is not the canonical runtime:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Verification

Validation command index:

- `docs/validation/README.md`

Baseline validation:

```bash
python -m pytest -q
python -m ruff check src tests core camera perception demos scripts
git diff --check
```

MediaPipeline checks:

```bash
python scripts/mediapipe/download_gesture_model.py
python -m pytest -q
python -m pytest -q tests/test_regression_media.py
python scripts/mediapipe/check_regression_media.py
python scripts/mediapipe/check_regression_media.py --strict
```

`tests/test_regression_media.py` validates the manifest without a physical
camera. Clip executions are skipped until the files declared in
`data/mediapipe/regression_media/manifest.json` are present, so that state is not a Phase 5 PASS.
Strict regression media checks are expected to fail while required Phase 5
primary clips are missing.

Current MediaPipeline state and camera-dependent TODOs are tracked in:

- `docs/mediapipeline/current_state.md`
- `docs/mediapipeline/recording_plan.md`

Webcam and RealSense RGB regression suites are separate. The RealSense suite is
deferred until camera access is available because RealSense behavior may differ
from webcam behavior.

Diagnostic script:

- `scripts/mediapipe/diagnose_gesture_channel_order.py` compares direct OpenCV camera
  frames with BGR-to-RGB converted frames when debugging camera-specific
  MediaPipe canned-label failures. It is diagnostic only and is not part of
  normal validation.

## Model Artifact Policy

Recommended policy: track the checksum, keep the model binary external/local.

- `data/mediapipe/models/gesture_recognizer.task.sha256` should be tracked. It defines
  the expected SHA-256 for the MediaPipe gesture recognizer artifact.
- `data/mediapipe/models/gesture_recognizer.task` should remain local or be provided by
  external artifact storage. Do not add it to normal git history unless the
  owner explicitly chooses to track the binary or use Git LFS.
- `scripts/mediapipe/download_gesture_model.py` recreates the local model and verifies it
  against the checksum when the checksum file exists.
- Runtime code must not download the model automatically.
- A missing model should fail clearly with setup instructions, not silently
  fetch a model or substitute fake media/model data.

## Roadmap

Near-term:

- Keep README and this document synchronized with code.
- Maintain tests around mock interfaces, replay execution, workspace config,
  README command truthfulness, and MediaPipeline boundaries.
- Replace stubs with concrete implementations one package at a time.

Planned later:

- Real SO-101/LeRobot driver.
- RealSense D435 validation and integration hardening.
- Workspace perception for bin colors and loadout occupancy.
- Manual image parsing for color sequences.
- Integration of MediaPipeline gesture events into a future command flow after
  acceptance criteria are met.
- Possible RAG/model providers once the interface requirements are known.

## Decision Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-04-29 | Keep repo and rewrite in place | Existing config/session/pose utilities are worth preserving. |
| 2026-04-29 | Four-layer architecture | Matches physical boundaries and keeps modules testable. |
| 2026-04-29 | CLI first, gesture second | Get the utility and dock loop stable before gesture input. |
| 2026-05-03 | README separates truth from roadmap | Prevents humans and agents from treating planned commands as current. |
| 2026-05-03 | `pyproject.toml` is the dependency source | Avoids dependency drift between duplicated files. |
| 2026-05-03 | Workspace config lands before camera/manual/autonomy work | It is shared infrastructure for later packages. |
| 2026-05-03 | No premature `rag` or `ai` extras | Future model support is possible but not designed yet. |
| 2026-05-07 | Conda is the canonical runtime; `.venv/` is local-only | Keeps full-program runtime reproducible while allowing editor/test/agent convenience environments. |
