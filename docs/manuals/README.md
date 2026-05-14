# Manual Reader Lane

Status: manual_reader v0 / Prototype-Partial.

- Code path: `manuals/`
- CLI/script: `scripts/manuals/read_manual.py`
- User guide: `docs/manuals/manual_reader.md`
- Data: `data/manuals/raw/`
- Tests: `tests/test_manual_reader.py` and `tests/test_manual_color_detector.py`

Boundary rule: manual_reader must stay independent from MediaPipe, LeRobot,
camera, and perception unless a future narrow interface is explicitly added.

Known limitation: the current reader needs stronger real-image ground-truth
validation before its color/count output should be treated as reliable.
