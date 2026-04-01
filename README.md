# Project: Dum-E
Hanyang University ERICA - Capstone Project

An autonomous tool-providing assistant built on the SO-101 arm (LeRobot / Hugging Face). The robot recognizes workspace context and provides tools or resource boxes to assist with assembly and maintenance tasks.

***BELOW IS PLAN FOR SYSTEM - NOTHING IN README OR PROJECT IS FINAL AND IS SUBJECT TO CHANGE***


TODO:
QOL systems
- easy lerobot motor id setup, calibration setup
- easier motion recorder and replayer
- easier storage and lerobot interface

## Overview

The system operates as a state machine with two main phases: **Warm Up** (environment verification) and **Active** (tool providing loop). It uses a fixed overhead camera (RealSense D435) for perception and the LeRobot framework for arm control.

## Hardware

- **Robot Arm:** SO-101 (LeRobot / Hugging Face stack)
- **Camera:** Fixed overhead RealSense D435 (depth + RGB)
- **Workstation:** Ubuntu 24.04
- **Gripper + Tool Rack:** Known fixed positions (POC scope)

## System Architecture

### Warm Up Phase

On startup, the arm initializes to its **Robot Base** position, then runs **Analyze Environment** — a set of verification checks that confirm the system is ready:

- **Verify Workspace** — confirm workspace is visible and calibrated
- **Verify Loadout** — confirm tool rack contents match expected configuration
- **Verify Manual** — confirm the assembly manual/instructions are accessible
- **Verify Dock** — confirm the delivery dock (drop zone) is clear and reachable
- **Verify Actor** — confirm user/operator is detected in the workspace

All checks must pass before transitioning to the Active phase.

### Active Phase

The Active phase is a loop centered around a **Standby** state:

1. **Standby** — arm is idle, waiting for the next task trigger
2. **Points to Manual Section** — system identifies which step of the assembly manual is active
3. **Analyze Section** — breaks down the current manual section:
   - **Isolate Section** — extract the relevant portion of the instructions
   - **Infer Loadout** — determine which tools/parts are needed for this step
4. **Dock Management** (green sub-region):
   - **Dock has space?** — check if the delivery dock can accept new items
     - **Yes →** proceed to **Fetch New Loadout** → **Set Dock** (place tools in dock)
     - **No →** **Clear Dock** (return items), then loop back to fetch
5. After dock is set, return to **Standby** and wait for the next section

## Tech Stack

| Layer | Tool |
|-------|------|
| Arm control | LeRobot (Hugging Face) |
| Camera | pyrealsense2 (RealSense SDK) |
| Object detection | YOLOv8 / RT-DETR |
| Hand tracking | MediaPipe |
| Calibration | OpenCV + ArUco markers |
| IK / FK | ikpy + SO-101 URDF |
| Orchestration | Python |

## Development Stages

| Stage | Focus | Description |
|-------|-------|-------------|
| 0 | Foundation | Arm setup, camera setup, calibration |
| 1 | Manual input | Provide tools based on manual button/keyboard input |
| 2 | Fixed sequence | Provide tools in a predefined assembly order |
| 3 | Workspace recognition | Detect tools/parts on workspace, track state |
| 4 | Intent recognition | Predict which tool the user needs next |
| 5 | Collision avoidance | Detect and avoid humans during arm movement |

## Project Structure

```
├── README.md
├── positions.json          # Saved arm positions (base, dock, rack, etc.)
├── config/
│   └── workspace.yaml      # Workspace bounds, dock location, rack positions
├── src/
│   ├── warmup/             # Environment verification checks
│   ├── perception/         # Camera, detection, hand tracking
│   ├── planner/            # Section analysis, loadout inference
│   ├── dock/               # Dock management (clear, fetch, set)
│   └── control/            # Arm movement, IK, safety
└── manuals/                # Assembly manual definitions
```

## Current Scope (POC)

| Aspect | POC | Full Version |
|--------|-----|--------------|
| Camera | Fixed overhead only | Fixed + arm-mounted |
| Tool rack | Fixed known positions | Any position |
| Grasp verification | Open-loop (assume success) | Visual confirmation |
| Delivery | Fixed drop zone (dock) | To user's hand |
| Manual input | Predefined steps | Dynamic recognition |

## Related

- [LeRobot (Hugging Face)](https://github.com/huggingface/lerobot)
- [SO-ARM100 URDF](https://github.com/TheRobotStudio/SO-ARM100)
- [RealSense SDK](https://github.com/IntelRealSense/librealsense)
