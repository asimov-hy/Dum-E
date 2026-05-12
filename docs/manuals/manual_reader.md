# Manual Reader

The manual reader is a standalone version 0 subsystem for extracting colored
block requirements from manual images as plain text.

## Input

Put manual images in:

```text
data/manuals/raw/
```

Images are processed in filename order. For `--stage next`, the reader uses the
first available image by filename.

## Output

Extracted text is written to:

```text
data/manuals/extracted/
```

The default `next` stage output path is:

```text
data/manuals/extracted/next_stage.txt
```

## CLI Usage

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next
```

To save and open an annotated visual debug preview:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --show
```

To hide colors from the detected counts while marking them differently in the
preview:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --show --ignore-color black --ignore-color white --ignore-color gray
```

To ignore specific manual/background RGB colors before region detection:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next --show --ignore-hex "#ffffff" --ignore-hex "#111111" --hex-tolerance 30
```

Example output:

```text
Stage: next
Required colored blocks:
- red: 2
- blue: 1
- yellow: 4
```

## Visual Debugging

`--show` writes an annotated preview image to:

```text
data/manuals/extracted/next_stage_preview.png
```

Use `--preview-output PATH` to choose a different path. The preview outlines
detected colored regions and labels them when the available image backend can
draw text. Ignored colors are excluded from text output and counts; known
ignored colors are marked differently in the preview.

Use `--ignore-hex HEX` for manual-specific colors such as page backgrounds,
printed graphics, outlines, or non-block artwork. It can be repeated. The
`--hex-tolerance N` option controls RGB distance matching and defaults to `25`;
larger values remove colors close to the supplied hex value.

If the system image viewer cannot be opened, the CLI prints the preview path
instead of crashing.

## Current Limits

- Output is text-only unless `--show` is passed.
- The reader is not connected to robot control.
- The reader does not import LeRobot, MediaPipe, or `src/dume/control`.
- Image loading and preview writing use OpenCV or Pillow only if one is already
  installed.
- Core color detection operates on RGB numpy arrays.
- Counts are best-effort estimates from colored image regions.

## Manual Validation

To verify real manual images, place representative photos or scans in
`data/manuals/raw/`, then run:

```bash
python3 scripts/manuals/read_manual.py --input data/manuals/raw --stage next
```

Inspect `data/manuals/extracted/next_stage.txt` and compare the reported block
colors and counts against the source image. Keep generated `.txt` outputs local;
commit only source images, docs, or code that are intentionally part of the
project.

## Future Path

The reader returns a structured `ManualStageResult` internally. A future robot
handoff can consume that type through a narrow interface after the manual-reading
workflow is validated.
