# Manual Data

Manual/reference inputs and manual-reader example artifacts live here without
coupling to MediaPipe or LeRobot data.

- `raw/`: original manual or reference images.
- `raw2/`: clean PNG manual fixtures from the second manual capture set.
- `raw3/`: clean PNG manual fixtures used for active color-set validation.
- `processed/`: normalized manual assets generated from raw inputs.
- `extracted/`: extracted text, tables, figures, structured outputs, and the
  tracked example preview artifact.
- `annotations/`: human-reviewed notes or labels for manual-derived assets.

Current contents:
- `raw/manual2-c1.jpg` through `raw/manual2-c5.jpg` are original manual/reference
  images moved from the repository root.
- `raw2/manual2-c1.png` through `raw2/manual2-c5.png` are clean PNG fixtures.
- `raw3/manual2-c1.png` through `raw3/manual2-c5.png` are clean PNG validation
  fixtures for current active color-set checks.
- `extracted/next_stage_preview.png` is an intentionally tracked example preview
  artifact. Other generated manual-reader text or debug preview outputs should
  stay local unless explicitly promoted as fixtures or examples.

Do not put MediaPipe regression media or LeRobot datasets in this tree.
