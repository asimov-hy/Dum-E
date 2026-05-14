# Manual Reader

The manual reader is a standalone version 0 subsystem for extracting current
step LEGO block color requirements from manual images as plain text and a
structured result.

## Input

Put manual images in:

```text
data/manuals/raw/
```

Images are processed in filename order. For `--stage next`, the reader uses the
first available image by filename.

## Output

By default the CLI prints to the terminal only. It does not write extracted text,
previews, or cached readings unless an output path is provided.

Use `--output-dir PATH` to write extracted text. Use `--clear-output-dir` with
`--output-dir` to remove prior generated manual-reader outputs in that directory
before writing.

## CLI Usage

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next
```

Default mode is `--mode new-pieces`, which counts only components classified as
`ACTIVE_BLOCK`. If no arrow/new-piece indicator is detected, the reader returns
status `no new-piece indicator detected` instead of counting the whole page.

For a debug/fallback pass that counts visible block-like components after
rejecting text, arrows, and background:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode visible-blocks
```

To save an annotated visual debug preview:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --preview-output /tmp/manual_debug.png
```

To print component classifications:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --debug-components
```

Example output:

```text
Stage: next
Mode: new-pieces
Status: ok
Required colored blocks:
- green: 2
```

## Visual Debugging

Use `--preview-output PATH` to write a preview. `--show` also writes a preview,
using a temporary `/tmp/manual_reader_*.png` path when no explicit path is
provided, then attempts to open it with the system viewer.

The preview labels accepted `ACTIVE_BLOCK` boxes and rejected `ARROW`, `TEXT`,
`DIMMED_OLD_BLOCK`, `BACKGROUND`, and `UNKNOWN` boxes with rejection reasons.
This is intended for classical-CV tuning, not for persistent cache storage.

If the system image viewer cannot be opened, the CLI prints the preview path
instead of crashing.

## Current Limits

- Default output is terminal-only unless `--output-dir`, `--preview-output`, or
  `--show` is passed.
- The reader is not connected to robot control.
- The reader does not import LeRobot, MediaPipe, or `src/dume/control`.
- Image loading and preview writing use OpenCV or Pillow only if one is already
  installed.
- Core detection uses classical component classification over RGB/HSV/gray numpy
  arrays. It does not use OCR, CNNs, transformers, SAM, YOLO, or MediaPipe.
- Counts are best-effort estimates from components classified as active blocks.

## Manual Validation

To verify real manual images, place representative photos or scans in
`data/manuals/raw/`, then run:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next
```

For visual inspection:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode new-pieces --debug-components --preview-output /tmp/manual_debug.png
```

Compare terminal output and the preview against the source image. Keep generated
`.txt` and preview outputs local; commit only source images, docs, or code that
are intentionally part of the project.

## Future Path

The reader returns a structured `ManualStageResult` internally with page
filename, mode, status, color counts, accepted components, rejected components,
and warnings. A future page loop, gesture confirmation, or robot handoff can
consume that type through a narrow interface after validation.
