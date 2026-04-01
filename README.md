# Project: Dum-E
Hanyang University ERICA capstone project

Dum-E is currently being shaped into a utility-first control toolkit for a LeRobot-based arm. The immediate goal is not autonomy. The goal is to make arm bring-up, motor setup, calibration, teleoperation, pose capture, and replay easy enough that later autonomy work has a stable base.

## Current Direction

The repo now focuses on four practical operator workflows:

1. discover and rename motor IDs
2. keep calibration metadata in one place
3. store named poses and motion skeletons in predictable files
4. inspect what a replay would do before wiring in hardware execution

This keeps the project grounded in repeatable low-level control before adding perception, planning, or tool-delivery logic.

## Utility Commands

After installing in editable mode, the CLI entrypoint is `dume`.

```bash
pip install -e .
dume init
dume status
dume motors scan
dume motors set-id --name shoulder_pan --to-id 7
dume calibrate show
dume poses save home --joints 0,0,0,0,0,0
dume motions scaffold pickup_demo --poses home,rack_approach,dock_approach
dume replay pose home
dume replay motion pickup_demo
```

The current framework is intentionally hardware-light. It manages structure, naming, and storage first, so LeRobot-specific motor and teleop implementations can be plugged in without rewriting the project layout again.

## Storage Layout

```text
config/
  hardware.yaml       # serial settings and expected motor ID map
  calibration.yaml    # offsets, inversion, limits, default home pose
data/
  poses.json          # named joint-space poses
  motions/            # one JSON file per motion skeleton or recording
logs/                 # reserved for future runtime logs
src/dume/control/
  motors.py
  calibration.py
  teleop.py
  recording.py
  replay.py
  session.py
```

## Naming Rules

- pose names use lowercase `snake_case`
- motion names use lowercase `snake_case`
- use semantic names like `home`, `rack_approach`, `pickup_screwdriver_v1`
- keep timestamps as metadata, not as the main identifier

## Near-Term Milestones

1. LeRobot-backed motor scan and ID reassignment
2. guided calibration workflow
3. safe joint teleop
4. pose capture from live hardware
5. motion replay with speed and safety checks

## Related

- [LeRobot (Hugging Face)](https://github.com/huggingface/lerobot)
- [SO-ARM100 URDF](https://github.com/TheRobotStudio/SO-ARM100)
