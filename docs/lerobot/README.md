# LeRobot Notes

Design notes specific to future LeRobot integration belong here.

Current status:
- No real LeRobot driver is implemented yet.
- The optional camera adapter placeholder lives at
  `src/dume/integrations/lerobot/camera_adapter.py`.
- Future LeRobot data belongs in `data/lerobot/`.
- Future LeRobot utilities belong in `scripts/lerobot/`.

Boundary rule:
- LeRobot integration must not directly depend on manual-reading or MediaPipe
  code. Keep adapters under `src/dume/integrations/lerobot/`, not a top-level
  Python package.
