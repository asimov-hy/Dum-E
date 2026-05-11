# DUM-E MediaPipeline Regression Media

`manifest.json` declares the Phase 5 regression clips. The clip paths are
relative to this directory unless `DUME_TEST_MEDIA_DIR` points at an external
media root.

The repository currently ships the manifest template but not the recorded clips.
Set each clip's `present` field to `true` after placing the file at the listed
path. Phase 5 is not a full PASS until the clips are present and
`python -m pytest -q tests/test_regression_media.py` runs against them.

## Suites

- `primary`: required for Phase 5 full PASS. Missing `required_for_phase5=true`
  clips keep Phase 5 at PARTIAL PASS.
- `webcam`: optional compatibility suite for webcam behavior.
- `realsense_rgb`: optional compatibility suite for RealSense RGB behavior.
  Keep this separate from webcam because the two sources can behave differently.
- `custom`: local experiments and future acceptance candidates.

Set `required_for_acceptance=true` only when an optional camera-specific clip
must block final acceptance.

Required clip coverage:

- Clear thumbs up, fist, palm.
- Index only, index + middle, index + middle + ring.
- Middle only, ring only, thumb + index, and no hand as `NONE` rejection clips.
- Four fingers with thumb folded.
- Partial hand entering/leaving, poor lighting, motion blur, two hands visible.
- Side-angle thumbs up, three-finger ring stress, and Victory/None raw-label
  oscillation.

Generated reports can be written outside the repo with:

```bash
DUME_REGRESSION_REPORT=/tmp/dume_regression_report.json \
python -m pytest -q tests/test_regression_media.py
```

Check media status without MediaPipe or camera hardware:

```bash
python scripts/mediapipe/check_regression_media.py
python scripts/mediapipe/check_regression_media.py --suite realsense_rgb
python scripts/mediapipe/check_regression_media.py --strict
```

Strict mode is expected to fail until the required primary clips exist.

Record a future clip:

```bash
python scripts/mediapipe/record_regression_clip.py \
  --source webcam \
  --output data/mediapipe/regression_media/webcam/thumbs_up_clear.mp4 \
  --clip-id webcam_thumbs_up_clear \
  --expected THUMBS_UP \
  --suite webcam \
  --camera-backend webcam \
  --duration-seconds 5 \
  --notes "clear thumbs up with laptop webcam"
```

Do not add fake media or set `present=true` until a real readable clip exists.
