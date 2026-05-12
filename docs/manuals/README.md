# Manual Reading Notes

Design notes and validation plans for future manual-reading work belong here.

Current status:
- No manual-reading package or runtime parser exists yet.
- Manual/reference source images live in `data/manuals/raw/`.
- Future processed outputs should stay under `data/manuals/processed/`,
  `data/manuals/extracted/`, or `data/manuals/annotations/`.
- Future utilities belong in `scripts/manuals/`.

Boundary rule:
- Manual-reading work must not directly depend on MediaPipe or LeRobot code.
  Add a narrow shared interface only when a concrete workflow requires it.
