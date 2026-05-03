# Project: DUM-E

Hanyang University ERICA capstone project.

DUM-E is a utility-first foundation for an automatic tool provider built around an
SO-101 arm. The current repository focuses on safe configuration, pose storage,
motion scaffolding, replay planning, and mock-first interfaces that future robot,
camera, manual, autonomy, and model features can plug into.

## What Works Today

Implemented package:

- `src/dume/control/`: control-layer utilities for config, calibration metadata,
  motor ID metadata, pose storage, motion storage, replay planning, and mockable
  arm/teleop interfaces.
- `src/dume/logging.py`: project logger helpers and file logging setup.

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

Documentation rule: no command, package, or feature may appear as current in this
README unless it exists in the repository. Planned work belongs in the roadmap.

## Install And Development

Python requirement: Python >= 3.10.

Use `pyproject.toml` as the single dependency source.

With `venv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

With conda:

```bash
conda create -n dume python=3.10
conda activate dume
pip install -e ".[dev]"
```

Run checks:

```bash
pytest -q
ruff check src tests
```

`requirements.txt` and `requirements-dev.txt` are intentionally not used. Add
optional dependency groups only when the corresponding code needs them.

## Architecture

Current dependency direction:

```text
control/ owns hardware-adjacent utilities and shared interfaces today
planned autonomy/ will coordinate control/, camera/, and manual/
```

Rules:

- Planned `control/`, `camera/`, and `manual/` layers should not import from
  each other.
- Planned `autonomy/` coordinates data flow between layers.
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
logs/
src/dume/
  main.py
  config.py
  logging.py
  control/
tests/
docs/
```

## Roadmap

Near-term:

- Create mock-first camera, manual, and autonomy packages one package at a time.
- Add `src/dume/camera/`, `src/dume/manual/`, and `src/dume/autonomy/` only when
  their first scoped interfaces/tests are part of the same change.
- Add optional extras only when needed, such as `camera`, `manual`, and `gesture`.
- Keep all hardware-facing code testable without the robot attached.

Later possibilities:

- RealSense D435 frame capture and workspace perception.
- Manual image parsing for LEGO brick color sequence extraction.
- Gesture input through MediaPipe Hands.
- Real SO-101/LeRobot arm driver.
- RAG or model-provider support after the interface and dependency needs are
  known. Do not add `rag` or `ai` extras before real code exists.
