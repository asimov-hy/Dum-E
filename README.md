# Project: DUM-E

Hanyang University ERICA capstone project

DUM-E is an automatic tool provider built on a LeRobot-based SO-101 arm. The system watches an operator work through assembly instructions and delivers the correct tools and materials to a handoff area, clearing and restaging as needed.

The current scope is a **LEGO brick provider**: the robot reads a pre-loaded visual manual, identifies which colored brick bin is needed for each step, moves that bin from storage to a loadout area, and waits for the operator's next command. The operator controls the flow through CLI commands first, with gesture-based control (MediaPipe Hands via RealSense D435) planned as a second pass.

## How It Works

1. **Warm-up** — the system verifies the workspace: camera connected, bins detected and colors mapped, manual loaded, loadout area clear, operator present.
2. **Active loop** — the operator advances to the next manual step. The system identifies the required color, checks if the loadout area has space (capacity: 2 bins), clears it if needed, fetches the correct bin from storage, places it in the loadout area, and returns to standby.
3. **Operator control** — CLI commands (`next`, `fetch N`, `stop`, `fault-reset`) drive the loop. Gesture control (thumbs up, open palms, finger count) replaces CLI in the second pass.

## Architecture

DUM-E is a single Python package with four modular layers. The main controller coordinates between sub-modules; sub-modules never import from each other directly.

```
Main Controller (autonomy/)
  ├── Robot Controller (control/)   — arm movement, calibration, poses, replay
  ├── Camera (camera/)              — RealSense pipeline, bin detection, gesture, actor presence
  └── Manual Reader (manual/)       — image parsing, color sequence, loadout planning
```

## Project Layout

```
config/
  hardware.yaml           # serial settings and motor ID map (SO-101, 6x sts3215)
  calibration.yaml        # joint offsets, inversion, limits, home pose
  workspace.yaml          # camera pose, bin positions, loadout area, actor zone
data/
  poses.json              # named joint-space poses (home, rack_approach, dock_approach, ...)
  motions/                # one JSON file per motion skeleton or recording
  manuals/                # pre-uploaded manual step images
logs/                     # runtime logs
src/dume/
  main.py                 # CLI entrypoint
  config.py               # shared Pydantic data models
  control/                # robot arm layer
    session.py            #   ControlSession — central config/data owner
    arm.py                #   ArmDriver interface (LeRobot plugs in here)
    motors.py             #   motor scan and ID management
    calibration.py        #   calibration metadata
    teleop.py             #   teleop interface
    recording.py          #   pose/motion storage (PoseStore)
    replay.py             #   replay planning and execution
  camera/                 # perception layer
    pipeline.py           #   RealSense D435 connection and frame capture
    workspace.py          #   bin color detection, loadout area occupancy
    gesture.py            #   MediaPipe Hands gesture classification
    actor.py              #   operator presence detection
  manual/                 # manual interpretation layer
    provider.py           #   loads manual images, outputs color sequence
    planner.py            #   maps color to bin position (LoadoutPlanner)
  autonomy/               # main controller and state machine
    states.py             #   state enum (17 states)
    runner.py             #   StateMachineRunner
    context.py            #   RunContext (shared runtime state)
    dock.py               #   dock management orchestrator
    controller.py         #   main controller coordinating all layers
tests/
```

## CLI Commands

```bash
pip install -e .

# Utility (robot controller)
dume init                          # create default config and data files
dume status                        # show config and storage summary
dume motors scan                   # show expected motor map
dume motors set-id --name gripper --to-id 9
dume calibrate show                # show calibration metadata
dume poses list                    # list saved poses
dume poses save home --joints 0,0,0,0,0,0
dume motions scaffold pickup_demo --poses home,rack_approach,dock_approach
dume replay pose home              # inspect or execute a pose replay
dume replay motion pickup_demo     # inspect or execute a motion replay

# Camera
dume camera status                 # check RealSense connection
dume camera snapshot               # capture a test frame

# Manual
dume manual load data/manuals/     # load and parse manual images
dume manual show                   # display parsed color sequence

# Autonomy (main controller)
dume run                           # start the autonomy loop
dume run --max-cycles 3            # run for 3 active loops then stop
```

## Current POC Scope

- **Bricks**: 3 colors (green, white, blue), one per bin, expandable
- **Storage**: separated bins at mostly-fixed positions, color-to-position mapped at startup via camera
- **Loadout area**: holds up to 2 bins
- **Robot action**: moves entire bins between storage and loadout area
- **Manual**: pre-loaded step images parsed into a color sequence before the run
- **Operator input**: CLI first, gesture control second
- **Camera**: RealSense D435 for workspace perception and gesture recognition
- **Arm**: SO-101 with LeRobot integration (6x sts3215 servos)

## Naming Rules

- Pose names: lowercase `snake_case` (e.g., `home`, `rack_approach`)
- Motion names: lowercase `snake_case` (e.g., `pickup_green`, `clear_loadout`)
- Semantic names over timestamps (e.g., `dock_place_v2` not `motion_20260429`)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/
```

## Related

- [LeRobot (Hugging Face)](https://github.com/huggingface/lerobot)
- [SO-ARM100 URDF](https://github.com/TheRobotStudio/SO-ARM100)
- [MediaPipe Hands](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
- [Intel RealSense D435](https://www.intelrealsense.com/depth-camera-d435/)