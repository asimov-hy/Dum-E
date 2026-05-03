# DUM-E Technical Documentation

> **Purpose**: Living technical reference for the DUM-E project. Contains current development status, architecture decisions, interface contracts, and implementation details. Updated continuously as development progresses. Intended for use as RAG context in AI-assisted development sessions.
>
> **Last updated**: 2026-04-29
> **Current phase**: Pre-implementation (utility layer exists, autonomy/camera/manual layers not started)

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| Name | DUM-E |
| Type | Automatic tool provider (LEGO brick provider for POC) |
| Hardware | SO-101 arm (LeRobot / Hugging Face), 6x sts3215 servos |
| Camera | Intel RealSense D435 |
| Gesture Model | MediaPipe Hands |
| Language | Python 3.10+ |
| Framework | Pydantic 2.7+, PyYAML 6.0+ |
| Package Manager | pip (editable install via pyproject.toml) |
| CLI Entrypoint | `dume` → `src/dume/main.py:app` |
| Repository | https://github.com/asimov-hy/Dum-E |

---

## 2. Architecture Overview

Four modular layers with one-directional dependency:

```
autonomy/ (Main Controller)
  ├── control/   (Robot Controller)
  ├── camera/    (Perception)
  └── manual/    (Manual Interpretation)
```

**Rule**: The main controller imports from all three sub-modules. Sub-modules never import from each other. If the manual reader needs a camera frame, the main controller gets it from camera and passes it in.

**Rule**: If autonomy discovers that a pose, config, or utility contract needs to change, that change goes into the utility layer (control/) first. Autonomy consumes it, never duplicates it.

---

## 3. Current Codebase Status

### 3.1 What Exists and Works

| File | Status | Description |
|------|--------|-------------|
| `config.py` | **Complete** | Pydantic models: SerialConfig, MotorConfig, HardwareConfig, JointCalibration, CalibrationConfig, PoseLibrary, MotionStep, MotionDefinition, ProjectPaths. YAML/JSON load/save utilities. |
| `control/session.py` | **Complete** | ControlSession: load from disk, bootstrap defaults, save_all, save_hardware, save_calibration, save_poses, status_summary. Central coordinator for the control layer. |
| `control/recording.py` | **Complete** | PoseStore: save/load/list poses, scaffold/load/list motions. snake_case validation via regex. Writes motion JSON to data/motions/. |
| `control/motors.py` | **Complete (config-only)** | MotorsService: scan returns config-backed motor records, set_motor_id updates hardware.yaml. No LeRobot bus communication yet. |
| `control/calibration.py` | **Complete (config-only)** | CalibrationService: sync_from_hardware creates calibration entries from motor list, current() returns stored calibration. No guided workflow or hardware interaction. |
| `main.py` | **Complete** | CLI: init, status, motors scan, motors set-id, calibrate init, calibrate show, teleop, poses list, poses save, motions list, motions scaffold, replay pose, replay motion. All via argparse. |
| `pyproject.toml` | **Complete** | Editable install, dume entrypoint, pytest + ruff dev deps. |
| `tests/test_config.py` | **Passing** | Tests session bootstrap and pose store scaffolding. |
| `tests/test_cli.py` | **Passing** | Tests CLI argument parsing and joint value parsing. |
| `config/hardware.yaml` | **Complete** | SO-101 default: 6 motors (shoulder_pan, shoulder_lift, elbow, wrist_pitch, wrist_roll, gripper), sts3215, /dev/ttyACM0 @ 1M baud. |
| `config/calibration.yaml` | **Complete** | Default calibration template: all offsets 0.0, no inversions, no limits set. |
| `data/poses.json` | **Complete** | Three starter poses: home [0,0,0,0,0,0], rack_approach, dock_approach. |

### 3.2 What Exists as Stubs

| File | Status | What's Missing |
|------|--------|----------------|
| `control/arm.py` | **Placeholder** | ArmController is a dataclass with in-memory state only. Needs: ArmDriver interface (ABC), MockArmDriver, future LeRobotArmDriver. |
| `control/teleop.py` | **Placeholder** | TeleopService.describe() returns a description string. Needs: TeleopDriver interface (ABC), MockTeleopDriver, future keyboard/gamepad implementation. |
| `control/replay.py` | **Partial** | ReplayService builds text plans (pose_plan, motion_plan). Needs: execute_pose and execute_motion methods that take an ArmDriver. |

### 3.3 What Does Not Exist Yet

| Package | Files Needed | Purpose |
|---------|-------------|---------|
| `camera/` | pipeline.py, workspace.py, gesture.py, actor.py | RealSense pipeline, bin detection, gesture recognition, actor presence |
| `manual/` | provider.py, planner.py | Manual image parsing, color-to-bin mapping |
| `autonomy/` | states.py, runner.py, context.py, dock.py, controller.py | State machine, main controller, dock management |
| `config/workspace.yaml` | — | Workspace layout, bin positions, loadout area, actor zone |
| `data/manuals/` | — | Directory for pre-uploaded manual step images |

---

## 4. Data Models (from config.py)

### Hardware

```python
SerialConfig:       port (str), baudrate (int)
MotorConfig:        name (str), motor_id (int), model (str), notes (str|None)
HardwareConfig:     robot_name (str), serial (SerialConfig), motors (list[MotorConfig])
```

### Calibration

```python
JointCalibration:   motor_name (str), offset_deg (float), inverted (bool), min_deg (float|None), max_deg (float|None)
CalibrationConfig:  home_pose (str), joints (list[JointCalibration])
```

### Poses and Motions

```python
PoseLibrary:        poses (dict[str, list[float]])
MotionStep:         pose (str|None), joints (list[float]|None), duration_s (float), hold_s (float)
                    # Validation: exactly one of pose or joints must be set
MotionDefinition:   name (str), frame (str), created_at (str), steps (list[MotionStep])
```

### Project Paths

```python
ProjectPaths:       root, config_dir, data_dir, motions_dir, logs_dir,
                    hardware_config, calibration_config, poses_file
                    # All derived from root via from_root(path)
```

### Workspace (planned, not yet in config.py)

```python
BinPosition:        index (int), x (float), y (float), z (float), label (str)
LoadoutArea:        capacity (int=2), x (float), y (float), z (float)
ActorZone:          x_min (float), x_max (float), y_min (float), y_max (float)
WorkspaceConfig:    camera_serial (str), bin_positions (list[BinPosition]),
                    loadout_area (LoadoutArea), actor_zone (ActorZone), safety_margin_m (float)
```

### Inventory Schema (planned)

```python
color:              str     — "green", "white", or "blue"
bin_position:       int     — storage position index (0, 1, 2)
in_storage:         bool    — bin is in its storage position
in_loadout:         bool    — bin is in the loadout area
```

---

## 5. Interface Contracts

### 5.1 Existing

**ControlSession** — central coordinator for the control layer
- `ControlSession.load(root: Path) → ControlSession` — loads or creates all config/data
- `session.bootstrap()` — creates default files
- `session.save_all()` — persists everything
- `session.status_summary() → dict` — returns motor count, pose count, motion count, etc.

**PoseStore** — pose and motion storage
- `save_pose(name, joints)` — validates snake_case, saves to poses.json
- `load_pose(name) → list[float]` — raises ValueError if unknown
- `list_poses() → dict[str, list[float]]` — sorted by name
- `scaffold_motion(name, pose_names) → MotionDefinition` — creates motion from pose sequence
- `load_motion(name) → MotionDefinition` — loads from data/motions/
- `list_motions() → list[str]` — sorted motion names

**MotorsService** — motor ID management
- `scan() → list[MotorScanRecord]` — returns configured motors (not live scan yet)
- `set_motor_id(name?, from_id?, to_id) → MotorConfig` — updates and persists

**CalibrationService** — calibration metadata
- `sync_from_hardware() → CalibrationConfig` — creates entries for all motors
- `current() → CalibrationConfig` — returns stored calibration

### 5.2 Planned

**ArmDriver** (interface, replaces ArmController)
- `connect() → None`
- `disconnect() → None`
- `move_joints(joints, speed) → bool`
- `read_joints() → list[float]`
- `is_connected() → bool`

**PerceptionService** (camera/ coordinator)
- Exposes: workspace checks, bin color detection, loadout occupancy, actor presence, gesture events
- Hides: RealSense SDK details, frame management, MediaPipe internals

**ManualProvider** (manual/ coordinator)
- `load(directory: Path) → ColorSequence` — parses manual images into ordered color list
- `get_step(index: int) → str` — returns color for step N
- `total_steps() → int`

**LoadoutPlanner**
- `plan(color: str, color_to_position: dict) → LoadoutRequest` — maps color to bin position
- Returns Fault-worthy error if color not found

**GestureService** (camera/gesture.py)
- Gesture set: thumbs_up → next_step, open_palms → pause, finger_count(N) → fetch_position_N
- Confidence threshold and cooldown to prevent accidental triggers
- Runs on RealSense RGB stream via MediaPipe Hands

**StateMachineRunner**
- `run(max_cycles: int | None, stop_event: Event | None) → None`
- max_cycles counts completed active loops only; warm-up is outside the count

**RunContext** — shared state across all states
- camera snapshot data, verification results (with cache/invalidation tracking)
- current manual step index, parsed color sequence, color-to-position mapping
- inferred loadout, stop/run metadata, lifecycle counters

---

## 6. State Machine

### 6.1 State List (17 states)

`RobotBase`, `AnalyzeEnvironment`, `VerifyWorkspace`, `VerifyLoadout`, `VerifyManual`, `VerifyDock`, `VerifyActor`, `Standby`, `PointsToManualSection`, `AnalyzeSection`, `IsolateSection`, `InferLoadout`, `FetchNewLoadout`, `SetDock`, `ClearDock`, `Fault`, `Stopped`

### 6.2 Warm-Up Phase
`RobotBase` → `AnalyzeEnvironment` (runs VerifyWorkspace, VerifyLoadout, VerifyManual, VerifyDock, VerifyActor sequentially) → `Standby`

- All five checks must pass before entering Active phase
- Failed checks retry only the failing state (max_retries configurable, default 3)
- Previously passed checks are cached within the same AnalyzeEnvironment run
- If a retry captures a new perception snapshot, perception-dependent passes are invalidated and must rerun
- Non-perception checks (VerifyManual) are never invalidated by a new frame
- Exceeding retry limit on any check → Fault

### 6.3 Active Phase
`Standby` → `PointsToManualSection` → `AnalyzeSection` (IsolateSection → InferLoadout) → dock management → `Standby`

- Dock management is non-state orchestration logic (dock_management function)
- If loadout area has space → FetchNewLoadout → SetDock → Standby
- If no space → ClearDock → re-check (bounded by max_dock_retries, default 3)
- Exceeding dock retries → Fault
- Exceeding color sequence length → Stopped
- Dock checks logged as: `dock_capacity_check | has_space={bool} | attempt={n}/{max}`

### 6.4 Post-Check Tiers
- **Tier 1 — Motion completion**: arm reached expected waypoint, no controller fault. Required for POC.
- **Tier 2 — Scene verification**: loadout area occupancy changed as expected. Required for POC.
- **Tier 3 — Object/grasp verification**: robot holds correct bin. Deferred to post-POC.

### 6.5 Operator Control
**Pass 1 (CLI)**: start, stop, fault-reset, next, fetch N
**Pass 2 (Gesture)**: thumbs up (next), open palms (pause), finger count (fetch position N). CLI remains as fallback.

---

## 7. Physical Setup

| Component | Detail |
|-----------|--------|
| Arm | SO-101, 6 DOF, sts3215 servos, LeRobot framework |
| Camera | Intel RealSense D435 (fixed mount, views workspace) |
| Storage bins | 3 separated bins, one per color (green, white, blue) |
| Bin positions | Mostly fixed, color-to-position mapped at startup via camera |
| Loadout area | Fixed region, holds up to 2 bins |
| Robot action | Moves entire bins (not individual bricks) |
| Manual | Pre-loaded as step images before run, parsed into color sequence |

---

## 8. Hardware & Environment Manifest

The development machine is the same machine that runs DUM-E live with the robot. All processing (perception, gesture recognition, state machine) runs on this machine.

| Component | Value | Notes |
|-----------|-------|-------|
| **Development / Runtime OS** | Ubuntu 24.04 LTS | Single machine for dev and live operation |
| **Machine** | Laptop, no discrete GPU | All processing is CPU-bound |
| **Python** | TBD (verify with `python3 --version`) | Target: 3.10+ for Pydantic 2.x and type hint support |
| **Camera** | Intel RealSense D435 | USB 3.0 required for depth stream. SDK: pyrealsense2. Minimum depth range ~28cm. CPU-only, no GPU needed. |
| **Gesture Model** | MediaPipe Hands | Runs on CPU via RealSense RGB stream. Expect ~15-25 FPS on CPU-only laptop. Sufficient for gesture classification. |
| **Arm** | SO-101 (6 DOF, 6x Feetech sts3215 servos) | LeRobot framework for motor communication |
| **Arm Connection** | TBD (USB-to-TTL or direct USB from servo board) | Default config assumes `/dev/ttyACM0` @ 1M baud. Update `config/hardware.yaml` once determined. |
| **Serial Adapter** | TBD | If USB-to-TTL: note chipset (FTDI, CP2102, CH340) — affects driver and latency |

### Implications for Development
- **No GPU**: MediaPipe Hands and all OpenCV operations run on CPU. Avoid GPU-dependent libraries. Do not plan for CUDA or TensorRT acceleration in the POC.
- **Single machine**: No network latency between perception and control. Camera frames, gesture events, and motor commands all share the same process or local IPC.
- **USB bandwidth**: RealSense D435 (USB 3.0) and arm serial (USB 2.0 or USB-to-TTL) share the laptop's USB controller. If both are on the same USB hub, test for frame drops under load.
- **Laptop thermals**: sustained RealSense streaming + MediaPipe + motor polling may throttle on a laptop. Monitor CPU temps during extended test runs.

### How to Fill In TBD Fields
Run these on the dev machine and update the table:
```bash
python3 --version                          # Python version
lsusb                                      # check for RealSense and serial adapter
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null   # find serial port for arm
rs-enumerate-devices                       # RealSense firmware version (after installing librealsense2)
```

---

## 9. Branch Strategy

| Branch | Scope | Merge Target |
|--------|-------|-------------|
| `dev/utility` | Steps 1–3: control layer, config, poses, workspace schema | `main` after Step 3 checklist passes |
| `dev/autonomy` | Steps 4–13: state machine, camera, manual, gesture | `main` after Step 12 checklist passes |

**Rule**: `dev/autonomy` rebases from `dev/utility`, never the reverse. If autonomy needs a control-layer change, that change goes into `dev/utility` first.

---

## 10. Dependencies

### Current (in repo)
```
pydantic>=2.7
PyYAML>=6.0
pytest>=8.0 (dev)
ruff>=0.6 (dev)
```

### Planned
```
pyrealsense2>=2.55      # camera layer
opencv-python>=4.9      # manual parsing, image processing
mediapipe>=0.10         # gesture recognition (second pass)
```

---

## 11. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-29 | Keep repo, rewrite in place | config.py models, ControlSession, PoseStore, and tests are worth preserving |
| 2026-04-29 | Four-layer architecture (control, camera, manual, autonomy) | Matches physical boundaries; sub-modules testable in isolation |
| 2026-04-29 | Camera module owns RealSense pipeline + workspace + gesture + actor as sub-modules | Single physical device, shared frame stream, multiple consumers |
| 2026-04-29 | Sub-modules never import from each other | Main controller passes data between them; enables independent testing and swappable mocks |
| 2026-04-29 | CLI first, gesture second | Get the dock loop working before adding perception-based operator input |
| 2026-04-29 | Manual is pre-loaded images, not live scanning | Simplifies POC; live scanning deferred to post-POC |
| 2026-04-29 | Dock-capacity check is non-state orchestration logic | Avoids a state that only evaluates a boolean; keeps state list clean |
| 2026-04-29 | POC is open-loop manipulation with Tier 1 + Tier 2 post-checks | Tier 3 (grasp verification) deferred to post-POC |
| 2026-04-29 | RealSense D435 over ZED | Selected camera for the project |
| 2026-04-29 | 3 colors for POC (green, white, blue) | Minimal viable set, expandable |
| 2026-04-29 | Recovery poses cover supported action waypoints only | Not arbitrary positions; honest scope for fixed-motion POC |
| 2026-04-29 | Inventory mismatch policy is binary | Any missing color → Fault. No partial-match until post-POC. |
| 2026-04-29 | max_cycles = completed active loops | Warm-up runs once at startup, outside the count |
| 2026-04-29 | Warm-up retries only the failing check | Cache passes; invalidate perception-dependent results on new snapshot |

---

## 12. Update Instructions

When updating this document after completing a development step:

1. Update **Section 3** (Codebase Status) — move items from "Does Not Exist" to "Exists" with accurate status
2. Update **Section 5** (Interface Contracts) — move items from "Planned" to "Existing" once implemented, include actual method signatures
3. Add a row to **Section 10** (Decision Log) for any new architectural decisions
4. Update the **Last updated** date at the top
5. If a planned interface changed during implementation, update both Sections 5 and 6 to reflect the actual implementation