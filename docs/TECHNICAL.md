# DUM-E Technical Documentation

Purpose: canonical technical and RAG context for DUM-E. Keep this document
accurate enough that a new human or agent can start from it without inferring
repo state from stale roadmap text.

Last updated: 2026-05-03
Current phase: foundation scaffold with utility interfaces, workspace config,
logging helpers, and planned future packages.

## Agent Context Rules

- Label every subsystem as `Implemented`, `Stub`, or `Planned`.
- README may list a command or package as current only if it exists in code.
- Update this document in the same change as interface, command, config, or
  architecture changes.
- `pyproject.toml` is the dependency source. Do not restore requirements files
  unless deployment needs them.
- Do not add optional extras such as `rag` or `ai` before real code and
  dependencies exist.

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
| `camera/` | Planned | No package yet; RealSense/perception interfaces come in a later phase. |
| `manual/` | Planned | No package yet; manual parsing interfaces come in a later phase. |
| `autonomy/` | Planned | No package yet; state machine scaffolding comes in a later phase. |
| `README.md` | Implemented | Current truth plus roadmap; planned commands are not listed as current. |

## Architecture Rules

Layer direction:

```text
control/ is implemented today
planned autonomy/ coordinates control/, camera/, and manual/
```

Rules:

- Planned `autonomy/` coordinates runtime flow and passes data between subsystems.
- Planned `control/`, `camera/`, and `manual/` layers must not import from each
  other directly.
- Real hardware/perception/model code enters behind interfaces plus mocks.
- Avoid provider registries until there are at least two real implementations or
  a concrete config-driven switch.

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

Current dependency source: `pyproject.toml`.

Runtime:

```text
pydantic>=2.7
PyYAML>=6.0
```

Development:

```text
pytest>=8.0
ruff>=0.6
```

Future optional extras should be added only when their code requires them, for
example `camera`, `manual`, or `gesture`. RAG/model-provider support remains a
roadmap possibility and has no package or dependency group yet.

## Verification

Target baseline:

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

Latest local attempt on 2026-05-03:

- `python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- `pytest -q`: 16 passed.
- `ruff check src tests`: pending in this shell because `ruff` is not installed.

## Roadmap

Near-term:

- Keep README and this document synchronized with code.
- Add tests around mock interfaces, replay execution, workspace config, and
  README command truthfulness.
- Replace stubs with concrete implementations one package at a time.

Planned later:

- Real SO-101/LeRobot driver.
- RealSense D435 pipeline.
- Workspace perception for bin colors and loadout occupancy.
- Manual image parsing for color sequences.
- Gesture input through MediaPipe Hands.
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
