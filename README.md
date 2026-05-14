# Project: DUM-E

Hanyang University ERICA capstone project.

DUM-E is a utility-first foundation for an automatic tool provider built around an
SO-101 arm. The current repository is organized around three human-facing product
lanes: manual reading, robot movement, and gesture reading.

## What Works Today

Implemented and prototype packages:

- `src/dume/control/`: control-layer utilities for config, calibration metadata,
  motor ID metadata, pose storage, motion storage, replay planning, and mockable
  arm/teleop interfaces.
- `src/dume/logging.py`: project logger helpers and file logging setup.
- `manuals/`: manual_reader v0 helpers for extracting best-effort colored block
  requirements from manual images.
- `core/`, `camera/`, and `perception/`: DUM-E MediaPipeline contracts, camera
  frame sources, MediaPipe gesture recognition, geometry mapping, temporal
  filters, and a mock operator-presence boundary.
- `demos/gesture_demo.py`: final gesture demo for webcam, RealSense when
  installed, fake sources, and `video:<path>` recorded media.

Robot movement/control is still mock-first. Replay, teleop, and arm execution
paths use scaffolded services and mock drivers; the real SO-101/LeRobot hardware
driver is planned and not implemented yet.

Current CLI commands:

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

## Where Things Live

| Product lane | Current paths | Status |
| --- | --- | --- |
| `manual_reader` | Code: `manuals/`; script: `scripts/manuals/read_manual.py`; docs: `docs/manuals/`; data: `data/manuals/`; tests: `tests/test_manual_reader.py`, `tests/test_manual_color_detector.py` | Prototype-Partial / current v0 |
| `robot_movement` | Code: `src/dume/control/`; CLI: `src/dume/main.py` / `dume` commands; config: `config/`; data: `data/poses.json`, `data/motions/` | Prototype-Partial; mock/scaffold only; no real SO-101 driver yet |
| `gesture_reader` | Code: `core/`, `camera/`, `perception/`; demo: `demos/gesture_demo.py`; scripts: `scripts/mediapipe/`; docs: `docs/mediapipeline/`, `docs/mediapipe/`; data: `data/mediapipe/` | Prototype-Partial; Phase 0-4 code/infrastructure exists, Phase 5 recorded media missing |

Documentation rule: no command, package, or feature may appear as current in this
README unless it exists in the repository. Planned work belongs in the roadmap.

## Setup

Conda is the intended runtime environment for running the full DUM-E program.
`pyproject.toml` remains the Python package and dependency metadata source.

```bash
conda env create -f environment.yml
conda activate dume
python -m pip install -e ".[dev,camera,perception]"
```

Run checks:

```bash
python -m pytest -q
```

For full developer, agent, optional dependency, architecture, and validation
details, see `docs/TECHNICAL.md`.

Documentation map:

- `docs/TECHNICAL.md`: canonical RAG/developer context.
- `docs/validation/README.md`: validation command index.
- `docs/mediapipeline/`: MediaPipeline plan, status, checklist, and recording
  plan.
- `docs/manuals/`: manual_reader lane guide and user docs.
- `docs/mediapipe/`: MediaPipe-specific notes outside the MediaPipeline phase
  docs.
- `docs/lerobot/`: future LeRobot integration notes.
- `docs/repo_organization_audit.md`: repository organization history.

`.venv/` may be used locally for editor, test, or agent execution, but it is not
the canonical runtime environment.

`requirements.txt` and `requirements-dev.txt` are intentionally not used. Add
optional dependency groups only when the corresponding code needs them.

Phase 0 and camera-only tests do not require MediaPipe. Webcam/video sources use
OpenCV lazily. RealSense remains optional and is imported only when that backend
starts.

## MediaPipeline Setup

Download or verify the MediaPipe gesture model:

```bash
python scripts/mediapipe/download_gesture_model.py
```

The default model path is `data/mediapipe/models/gesture_recognizer.task`. The model
binary is a local/external artifact; the checksum
`data/mediapipe/models/gesture_recognizer.task.sha256` should be tracked so
`scripts/mediapipe/download_gesture_model.py` can recreate and verify the local model.
Runtime code does not download models automatically. A missing model causes
`GestureService` to raise with download instructions.

Run the final live demo:

```bash
python demos/gesture_demo.py \
  --source webcam \
  --log-observations \
  --log-events \
  --draw-landmarks \
  --draw-finger-state \
  --draw-filter-state
```

Supported demo source forms:

- `--source webcam`
- `--source realsense` when `pyrealsense2` and hardware are available
- `--source video:<path>` for recorded files
- `--show-flipped-display true` for display-only mirroring

The demo runs inference once per frame with:

```text
frame = source.get_frame()
observations = gesture.analyze_frame(frame)
events = gesture.events_from_observations(frame, observations)
```

Frames are not flipped before inference. RGB is converted to BGR only for
display.

## Recorded-Media Regression

The regression manifest lives at `data/mediapipe/regression_media/manifest.json`. Put clips at
the listed paths under `data/mediapipe/regression_media/`, or set `DUME_TEST_MEDIA_DIR` to an
external media root with the same relative paths. Set a clip's `present` field
to `true` once the file exists.

Current Phase 5 status is **PARTIAL PASS**: the harness and manifest exist, but
the required recorded clips are missing. See:

- `docs/mediapipeline/current_state.md`
- `docs/mediapipeline/recording_plan.md`

Run:

```bash
python -m pytest -q tests/test_regression_media.py
```

Check media status:

```bash
python scripts/mediapipe/check_regression_media.py
python scripts/mediapipe/check_regression_media.py --strict
```

Strict mode is expected to fail until required primary clips are recorded.

Record future clips:

```bash
python scripts/mediapipe/record_regression_clip.py \
  --source webcam \
  --output data/mediapipe/regression_media/webcam/thumbs_up_clear.mp4 \
  --clip-id webcam_thumbs_up_clear \
  --expected THUMBS_UP \
  --suite webcam \
  --camera-backend webcam \
  --duration-seconds 5
```

Camera-specific suites:

- `primary`: required clips for Phase 5 full PASS.
- `webcam`: optional compatibility clips.
- `realsense_rgb`: optional RealSense RGB compatibility clips. Keep these
  separate because RealSense behavior may differ from webcam behavior.

Optional report output:

```bash
DUME_REGRESSION_REPORT=/tmp/dume_regression_report.json \
python -m pytest -q tests/test_regression_media.py
```

The regression report separates six-target accuracy from `NONE` rejection
behavior. It records observed events, first detection timestamp, misses, false
positives, raw-label distribution, source distribution, latency, and
time-to-event. Phase 5 is not a full PASS until recorded clips are present and
the regression test runs against them rather than skipping missing media.

Required regression coverage includes clear target clips for `THUMBS_UP`,
`FIST`, `PALM`, `ONE_FINGER`, `TWO_FINGERS`, and `THREE_FINGERS`, plus
unsupported/no-hand clips for `NONE` rejection and stress clips for lighting,
motion blur, two hands, side angles, ring-finger oscillation, and raw-label
flicker.

Known MediaPipeline limitations:

- Ring-finger geometry can oscillate, especially for three-finger poses.
- Thumb detection is intentionally strict and handedness-dependent.
- Hand tilt can break simple image-space finger geometry.
- `max_num_hands=1` is the prototype default.
- Display mirroring is display-only and must not be applied before inference.
- Manual webcam validation for Phase 3 and Phase 4 remains outstanding unless
  recorded in the phase checklist.

## Architecture

Current dependency direction:

```text
control/ owns hardware-adjacent utilities and shared interfaces today
manuals/ owns manual_reader v0 parsing helpers
core/ owns MediaPipeline contracts
camera/ may import core/
perception/ may import core/
camera/ and perception/ do not import each other
future command flow may coordinate control, gesture, and manual outputs later
```

Rules:

- `core/`, `camera/`, and `perception/` stay separated by the MediaPipeline
  contracts.
- `manuals/` owns the current manual_reader v0 code and stays independent from
  MediaPipe, LeRobot, camera, and perception unless a narrow interface is added
  later.
- `src/dume/control/` owns robot/control/session logic and currently uses mock
  drivers/scaffolded replay and teleop paths.
- Manual-reading, MediaPipe/MediaPipeline, and LeRobot work have separate data,
  docs, and script lanes. Do not make those domains depend on each other
  directly.
- LeRobot integration code belongs under `src/dume/integrations/lerobot/`.
- New hardware, perception, manual, RAG, or model behavior should start behind a
  small interface plus a mock implementation.
- Avoid provider registries or factories until there are at least two real
  implementations or a concrete config-driven switch.

Project layout:

```text
config/
  hardware.yaml
  calibration.yaml
  workspace.yaml
data/
  poses.json
  motions/
  manuals/
    raw/
    processed/
    extracted/
    annotations/
  mediapipe/
    models/
    regression_media/
    diagnostics/
  lerobot/
    datasets/
    episodes/
    policies/
    calibration/
logs/
core/
camera/
perception/
demos/
scripts/
  manuals/
  mediapipe/
  lerobot/
src/dume/
  main.py
  config.py
  logging.py
  control/
  integrations/
tests/
docs/
```

## Roadmap

Near-term:

- Record the MediaPipeline regression clips declared in `data/mediapipe/regression_media/manifest.json`.
- Complete manual webcam validation for Phase 3 and Phase 4 gestures/filters.
- Strengthen manual_reader real-image ground-truth validation.
- Add new optional extras only when corresponding code needs them.
- Keep all hardware-facing code testable without the robot attached.

Later possibilities:

- RealSense D435 validation and workspace perception.
- Manual image parsing hardening for LEGO brick color sequence extraction.
- Integration of MediaPipeline gesture events into a future command flow after
  acceptance criteria are met.
- Real SO-101/LeRobot arm driver.
- RAG or model-provider support after the interface and dependency needs are
  known. Do not add `rag` or `ai` extras before real code exists.
