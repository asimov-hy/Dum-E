# LeRobot Integration

Future LeRobot adapters belong here. Keep this integration independent from
manual-reading and MediaPipe code.

Current status:
- `camera_adapter.py` is a placeholder boundary.
- It intentionally does not import LeRobot.
- `camera.source.create_source(backend="lerobot")` lazily delegates here.

Do not create a top-level `lerobot/` Python package for DUM-E integration code.
