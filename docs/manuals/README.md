# Manual Reader Lane

Status: Prototype-Partial / current v0.

Current purpose: read a manual page and output active/new block colors for the
current step. Later, that output can feed:

```text
manual page loop -> gesture confirmation -> robot/LeRobot tool-provider handoff
```

That handoff is not implemented yet.

## Index

- Code path: `manuals/`
- CLI: `scripts/manuals/read_manual.py`
- Guide: `docs/manuals/manual_reader.md`
- Tests: `tests/test_manual_reader.py`, `tests/test_manual_color_detector.py`

Boundary rule: manual_reader must stay independent from MediaPipe, LeRobot,
gesture, camera, perception, and robot/control unless a future narrow interface
is explicitly added.

Known limitation: clean PNG/manual images can over-count studs, faces, or
components. Counts are best-effort component counts; active color set/color
presence needs the next accuracy pass before output should be treated as
reliable LEGO brick quantities.
