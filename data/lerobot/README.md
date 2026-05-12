# LeRobot Data

Future LeRobot data lives here without coupling to manual-reading or MediaPipe data.

- `datasets/`: dataset exports or imported dataset pointers.
- `episodes/`: captured or replayable episode data.
- `policies/`: policy artifacts or local policy references.
- `calibration/`: calibration files used by LeRobot workflows.

No runtime LeRobot workflow is implemented yet. Keep generated or heavyweight
artifacts local unless the project owner chooses a tracking or external storage
policy.
