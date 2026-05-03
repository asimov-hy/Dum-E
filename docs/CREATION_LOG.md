# DUM-E Repo Update Guide — Creation Document

## Decision: Rewrite In Place, Don't Wipe

The current repo has useful infrastructure worth keeping. Wiping and starting fresh would mean rebuilding data models, session management, CLI parsing, project layout, and tests from scratch. Instead, update the existing files and add the new packages.

### What to Keep As-Is
- `pyproject.toml` — update dependencies, keep structure
- `config.py` — all Pydantic models (HardwareConfig, CalibrationConfig, PoseLibrary, MotionDefinition, ProjectPaths, load/save functions). These are well-designed and tested.
- `control/session.py` — ControlSession pattern (load, bootstrap, save_all, status_summary). This stays as the robot controller's coordinator.
- `control/recording.py` — PoseStore with pose save/load, motion scaffolding, snake_case validation. Solid and tested.
- `control/motors.py` — MotorsService config-backed scan and ID reassignment. Keep, extend later with LeRobot bus.
- `control/calibration.py` — CalibrationService sync and read. Keep, extend later.
- `main.py` — CLI entrypoint and argument parsing. Extend with new commands.
- `config/hardware.yaml` — SO-101 motor definitions
- `config/calibration.yaml` — joint calibration template
- `data/poses.json` — starter poses (home, rack_approach, dock_approach)
- `tests/` — both existing tests pass and should keep passing

### What to Rewrite
- `control/arm.py` — replace placeholder dataclass with a real interface that LeRobot can back later
- `control/teleop.py` — replace description string with actual stub interface
- `control/replay.py` — replace text-plan-only service with an interface that can execute when hardware is connected
- `README.md` — full rewrite (see Document 2)

### What to Add

#### New Packages

```
src/dume/
  camera/                  ← NEW: perception layer
    __init__.py
    pipeline.py            — RealSense D435 connection, frame capture, stream management
    workspace.py           — bin color detection, loadout area occupancy checks
    gesture.py             — MediaPipe Hands wrapper, gesture classification (second pass)
    actor.py               — operator presence detection
  manual/                  ← NEW: manual interpretation layer
    __init__.py
    provider.py            — loads manual images, parses color sequence
    planner.py             — maps color to bin position (LoadoutPlanner)
  autonomy/                ← NEW: main controller + state machine
    __init__.py
    states.py              — state enum (17 states)
    runner.py              — StateMachineRunner with run(max_cycles, stop_event)
    context.py             — RunContext (shared state across all states)
    dock.py                — dock_management orchestrator function
    controller.py          — main controller coordinating camera, manual, control
```

#### New Config Files

```
config/
  workspace.yaml           ← NEW: camera pose, loadout area region, 3 storage bin positions, actor zone, safety margins
```

#### New Data Directories

```
data/
  manuals/                 ← NEW: pre-uploaded manual step images
```

#### New Dependencies (add to requirements.txt as needed per step)

```
# Step 7 — Camera
pyrealsense2>=2.55

# Step 8 — Manual Reader
opencv-python>=4.9
# (optional: pillow for basic image handling)

# Step 11 — Gesture Control
mediapipe>=0.10
```

---

## Step-by-Step Repo Update Sequence

### Phase 1: Update Utility Layer (dev/utility)

#### 1. Update pyproject.toml
Add optional dependency groups for camera, manual, and autonomy:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
camera = ["pyrealsense2>=2.55"]
manual = ["opencv-python>=4.9"]
gesture = ["mediapipe>=0.10"]
all = ["pyrealsense2>=2.55", "opencv-python>=4.9", "mediapipe>=0.10"]
```

#### 2. Rewrite control/arm.py
Replace the placeholder dataclass with a proper interface:

```python
from __future__ import annotations
from abc import ABC, abstractmethod

class ArmDriver(ABC):
    """Interface for arm hardware drivers. LeRobot implementation plugs in here."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def move_joints(self, joints: list[float], speed: float = 0.5) -> bool: ...

    @abstractmethod
    def read_joints(self) -> list[float]: ...

    @abstractmethod
    def is_connected(self) -> bool: ...


class MockArmDriver(ArmDriver):
    """In-memory mock for testing without hardware."""

    def __init__(self) -> None:
        self._connected = False
        self._joints: list[float] = []

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def move_joints(self, joints: list[float], speed: float = 0.5) -> bool:
        self._joints = list(joints)
        return True

    def read_joints(self) -> list[float]:
        return list(self._joints)

    def is_connected(self) -> bool:
        return self._connected
```

#### 3. Rewrite control/teleop.py
Replace description string with a stub interface:

```python
from __future__ import annotations
from abc import ABC, abstractmethod

class TeleopDriver(ABC):
    """Interface for teleop input. Keyboard, gamepad implementations plug in."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_active(self) -> bool: ...


class MockTeleopDriver(TeleopDriver):
    """Stub for testing."""

    def __init__(self) -> None:
        self._active = False

    def start(self) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active
```

#### 4. Update control/replay.py
Keep the text plan methods, add an execution interface:

```python
# Add to existing ReplayService class:

def execute_pose(self, name: str, driver: ArmDriver) -> bool:
    """Execute a pose on hardware. Returns True if arm reached target."""
    joints = self.pose_store.load_pose(name)
    return driver.move_joints(joints)

def execute_motion(self, name: str, driver: ArmDriver) -> bool:
    """Execute a motion sequence on hardware. Returns True if all steps completed."""
    motion = self.pose_store.load_motion(name)
    for step in motion.steps:
        if step.pose:
            joints = self.pose_store.load_pose(step.pose)
        else:
            joints = step.joints
        if not driver.move_joints(joints):
            return False
    return True
```

#### 5. Add workspace.yaml config schema
Add to `config.py`:

```python
class BinPosition(BaseModel):
    index: int
    x: float
    y: float
    z: float
    label: str = ""  # color label populated at runtime by perception

class LoadoutArea(BaseModel):
    capacity: int = 2
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

class ActorZone(BaseModel):
    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0

class WorkspaceConfig(BaseModel):
    camera_serial: str = ""
    bin_positions: list[BinPosition] = Field(default_factory=list)
    loadout_area: LoadoutArea = Field(default_factory=LoadoutArea)
    actor_zone: ActorZone = Field(default_factory=ActorZone)
    safety_margin_m: float = 0.05
```

#### 6. Add data/manuals/ directory
Create `data/manuals/.gitkeep` to establish the directory.

#### 7. Update README.md
Replace with Document 2 content.

#### 8. Run existing tests
```bash
pytest tests/ -v
```
All existing tests must still pass after these changes.

---

### Phase 2: Add New Packages (dev/autonomy, after rebase)

#### 9. Create camera/ package
```
src/dume/camera/__init__.py
src/dume/camera/pipeline.py     — RealSense wrapper (stub first)
src/dume/camera/workspace.py    — bin detection, occupancy (stub first)
src/dume/camera/gesture.py      — empty file, built in second pass
src/dume/camera/actor.py        — presence detection (stub first)
```

#### 10. Create manual/ package
```
src/dume/manual/__init__.py
src/dume/manual/provider.py     — ManualProvider: loads images, outputs color sequence
src/dume/manual/planner.py      — LoadoutPlanner: color → bin position mapping
```

#### 11. Create autonomy/ package
```
src/dume/autonomy/__init__.py
src/dume/autonomy/states.py     — state enum (17 states)
src/dume/autonomy/runner.py     — StateMachineRunner
src/dume/autonomy/context.py    — RunContext
src/dume/autonomy/dock.py       — dock_management orchestrator
src/dume/autonomy/controller.py — main controller
```

#### 12. Extend CLI (main.py)
Add new top-level commands:

```
dume run              — start the autonomy loop (main controller)
dume run --max-cycles 3
dume run --stop
dume camera status    — check RealSense connection
dume camera snapshot  — capture and display a test frame
dume manual load DIR  — load and parse manual images from a directory
dume manual show      — display parsed color sequence
```

#### 13. Add new tests
```
tests/test_camera.py
tests/test_manual.py
tests/test_autonomy.py
tests/test_states.py
```

---

## Commit Sequence Recommendation

```
1. "refactor: replace arm/teleop/replay placeholders with proper interfaces"
2. "feat: add workspace config schema and manuals directory"
3. "docs: rewrite README for LEGO brick provider scope"
4. "feat: add camera package skeleton with pipeline and workspace stubs"
5. "feat: add manual package with provider and planner stubs"
6. "feat: add autonomy package with state machine skeleton"
7. "feat: extend CLI with run, camera, and manual commands"
```

Each commit should leave the repo in a passing-tests state.