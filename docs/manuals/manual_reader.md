# Manual Reader

The manual reader is a standalone Prototype-Partial / current v0 subsystem for
extracting active/new LEGO block colors from manual images as plain text and a
structured result. The current implementation is a role-based component
classifier, not a solved brick counter.

Current component roles:

- `ACTIVE_BLOCK`
- `DIMMED_OLD_BLOCK`
- `ARROW`
- `TEXT`
- `BACKGROUND`
- `UNKNOWN`

## Input

Put manual images in:

```text
data/manuals/raw/
```

Images are processed in filename order. For `--stage next`, the reader uses the
first available image by filename.

## Output

By default the CLI prints to the terminal only. It writes only when
`--output-dir` or `--preview-output` is provided.

Use `--output-dir PATH` to write extracted text. Use `--clear-output-dir` with
`--output-dir` to remove prior generated manual-reader outputs in that directory
before writing. Use `--preview-output PATH` to write an annotated visual preview.
During testing, prefer `/tmp` paths such as `/tmp/manual_debug.png` for debug
previews.

## Modes

- `new-pieces`: intended robot/tool-handoff mode. It counts and prints only
  components classified as `ACTIVE_BLOCK`.
- `visible-blocks`: debug/fallback mode for inspecting visible block-like
  components after rejecting text, arrows, and background.

## Statuses

- `ok`: active/new block candidates were found and the page was readable.
- `ok_no_arrow_detected`: active blocks were found, but no arrow was detected.
  Arrows are no longer required to detect active blocks.
- `no_new_piece_indicator`: no active block candidates were found.
- `ambiguous`: multiple plausible interpretations were found, if the current
  classifier emits that status.
- `last_page`: reserved for a later page-loop context that provides page order.
  Do not use it as a standalone single-page/manual-reader result today.

## CLI Usage

Default mode is `new-pieces`:

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces
```

`new-pieces` no longer requires arrows to detect active blocks.

To print component classifications and save an annotated preview:

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces \
  --debug-components \
  --preview-output /tmp/manual_debug.png
```

For a debug/fallback pass that counts visible block-like components after
rejecting text, arrows, and background:

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode visible-blocks \
  --preview-output /tmp/manual_visible_debug.png
```

Example output:

```text
Stage: next
Mode: new-pieces
Status: ok
Required active colors:
- green

Component counts:
- green: 2
```

## Visual Debugging

Use `--debug-components` to print role classifications and rejection reasons.
Use `--preview-output PATH` to write a preview.

The preview labels accepted `ACTIVE_BLOCK` boxes and rejected `ARROW`, `TEXT`,
`DIMMED_OLD_BLOCK`, `BACKGROUND`, and `UNKNOWN` boxes with rejection reasons.
This is intended for classical-CV tuning, not for persistent cache storage.

Use `--clear-output-dir` only with `--output-dir` when intentionally replacing
generated text outputs.

## Current Limits

- Default output is terminal-only unless `--output-dir` or `--preview-output` is
  passed.
- The reader is not connected to robot control.
- The reader does not import LeRobot, MediaPipe, or `src/dume/control`.
- Image loading and preview writing use OpenCV or Pillow only if one is already
  installed.
- Core detection uses classical component classification over RGB/HSV/gray numpy
  arrays. It does not use OCR, CNNs, transformers, SAM, YOLO, or MediaPipe.
- Required active colors are the primary `new-pieces` output.
- Component counts are secondary diagnostics from active-looking components.
  They are not reliable LEGO brick quantities because clean manual images can
  over-segment studs, faces, and highlights.
- The reader aggregates the active color set after component role
  classification, with extra rejection for arrow fragments, dimmed old assembly
  colors, and page/background-like white regions.

## Manual Validation

To verify real manual images, place representative photos or scans in
`data/manuals/raw/`, then run:

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces
```

For visual inspection:

```bash
python scripts/manuals/read_manual.py \
  --input data/manuals/raw \
  --stage next \
  --mode new-pieces \
  --debug-components \
  --preview-output /tmp/manual_debug.png
```

Compare terminal output and the preview against the source image. Keep generated
`.txt` and preview outputs local; commit only source images, docs, or code that
are intentionally part of the project.

Smoke target truth for `data/manuals/raw3` clean PNGs:

- C1: green.
- C2: green.
- C3: green and white.
- C4: green, white, and yellow.
- C5: green, white, and yellow.

## Future Path

The reader returns a structured `ManualStageResult` internally with page
filename, mode, status, active colors, diagnostic color counts, accepted
components, rejected components, and warnings. The final goal is to read a
manual page and output the active/new block colors needed for that step. After
validation, that output can feed:

```text
manual page loop -> gesture confirmation -> robot/LeRobot tool-provider handoff
```
