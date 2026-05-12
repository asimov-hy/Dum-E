# DUM-E Repository Organization Audit

Date: 2026-05-07
Branch: `main`

Repository Cleanup / Organization Result:
- Status: REPORT ONLY
- The repository was audited end to end, but the working tree is too broad and active for safe file moves or deletions in this pass.

Scope decision:
- Cleanup is too large/risky to act on immediately.
- No risky file moves/deletions were performed.
- Reason: the tree contains 12 modified tracked files, 28 untracked non-generated project files, untracked model/test-media scaffolding, and many ignored generated artifacts. More than 10 tracked or important files would need decisions before any meaningful reorganization.

Files changed:
- `docs/repo_organization_audit.md` - added this audit report so cleanup decisions are staged instead of mixed into MediaPipeline development.

Files moved:
- None.

Files deleted:
- None.

Files archived:
- None.

Files left unchanged:
- `data/mediapipe/models/gesture_recognizer.task` - model artifact; do not touch without explicit approval.
- `data/mediapipe/models/gesture_recognizer.task.sha256` - important checksum-like artifact; docs imply it should be preserved and likely committed.
- `data/mediapipe/regression_media/manifest.json` and `data/mediapipe/regression_media/README.md` - active Phase 5 regression scaffold; required clips are still honestly missing.
- `docs/mediapipeline/build_plan_v5.md`, `docs/mediapipeline/phase_verification_checklist.md`, `docs/mediapipeline/current_state.md`, `docs/mediapipeline/recording_plan.md` - current/canonical MediaPipeline planning and state docs.
- `docs/known_issues.md` - useful current/historical issue note, but needs review because it appears partly stale.
- `scripts/mediapipe/diagnose_gesture_channel_order.py` - useful diagnostic script, but undocumented and untracked.
- `tests/test_drop_none_filter.py` and `tests/test_filters_drop_none.py` - similar names but different coverage surfaces; left unchanged.
- `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `src/dume.egg-info/`, `.vscode/`, `.claude/settings.local.json` - ignored generated/local files; safe candidates for local cleanup, but left untouched by this report-only pass.
- Empty `core/__init__.py` and `perception/__init__.py` - intentional package markers.
- Empty `.agents/` and `.codex/` directories - local empty directories; not tracked.

Inventory summary:
- Source files: 30 Python files across `src/dume/`, `core/`, `camera/`, and `perception/`.
- Test files: 28 test files.
- Script files: 4 script files.
- Demo files: 2 demo files.
- Docs/RAG files: 8 main docs/RAG files, plus README files under `data/`.
- Data/model files: 14 config/data/manifest-like files and 2 model artifacts.
- Generated/cache files: 91 generated/cache files found outside `.git` and `.venv`; all observed examples are ignored by `.gitignore` or global git ignore.
- Unknown/needs-review files: `.vscode/browse.vc.db`, `.vscode/browse.vc.db-shm`, `.vscode/browse.vc.db-wal`; ignored local IDE database files.

Duplicate/confusing files found:
- `README.md`: top-level README plus `data/motions/README.md`, `data/mediapipe/regression_media/README.md`, and ignored `.pytest_cache/README.md`; left unchanged because the real README files have distinct scopes.
- `types.py`: `core/types.py` and `perception/types.py`; left unchanged because they define separate architecture-layer contracts.
- `__init__.py`: package markers in multiple packages; left unchanged.
- `.gitkeep`: `data/manuals/processed/.gitkeep` and `logs/.gitkeep`; left unchanged as intentional tracked placeholders.
- `docs/mediapipeline/build_plan_v5.md` and `docs/mediapipeline/phase_verification_checklist.md`: overlapping phase headings; left unchanged because one is the build plan and one is the verification checklist.
- `docs/mediapipeline/recording_plan.md`, `data/mediapipe/regression_media/README.md`, and README recorded-media sections: overlapping content; staged for later consolidation, not safe to merge automatically.
- `tests/test_drop_none_filter.py` and `tests/test_filters_drop_none.py`: confusing but not exact duplicates; staged for later test naming review.
- Ignored cache duplicates such as `__init__.cpython-312.pyc`, `CACHEDIR.TAG`, and cache `.gitignore` files; safe local cleanup candidates, not tracked.
- Pasted prompt dumps, `copy`, `backup`, `old`, `tmp`, `scratch`, or `draft` project files: none found outside generated/cache names.

Dependency/path checks:
- Imports checked: Python AST import scan across `core`, `camera`, `perception`, `src`, `demos`, `scripts`, and `tests`.
- Docs links checked: `rg` scan for MediaPipeline docs, model path, manifest path, scripts, and regression-media references.
- `pyproject.toml` references checked: package discovery remains `src` only, pytest `pythonpath` includes `.` and `src`, and optional groups include camera/perception/realsense/dev.
- Manifest paths checked: `data/mediapipe/regression_media/manifest.json` contains 21 clips, 0 present clips, and 19 missing `required_for_phase5` primary clips.
- CLI/script references checked: README and docs reference `scripts/mediapipe/check_regression_media.py`, `scripts/mediapipe/record_regression_clip.py`, and `scripts/mediapipe/download_gesture_model.py`; `scripts/mediapipe/diagnose_gesture_channel_order.py` is not documented.
- Any broken references found: no broken import-boundary references found; no candidate file was safe to move without reference updates.

MediaPipeline boundary check:
- `core/`, `camera/`, and `perception/` boundaries still hold by AST scan and tests.
- `core/` does not import `camera` or `perception`.
- `camera/` imports `core/` and camera modules, not `perception/`.
- `perception/` imports `core/` and perception modules, not `camera/`.
- `GestureService` behavior was untouched.
- Phase 5 remains PARTIAL PASS because required recorded clips are missing.
- Fake media was added: no.

Tests and checks run:
- `python3 -m pytest -q` - passed: 159 passed, 21 skipped.
- `python3 -m pytest -q tests/test_core_contracts.py tests/test_import_boundaries.py tests/test_camera_fake_source.py tests/test_camera_video_source.py tests/test_gesture_service_timestamp.py tests/test_canned_mapper.py tests/test_drop_none_filter.py tests/test_overlay_no_finger_state.py tests/test_finger_state_detector.py tests/test_gesture_mapper_geometry.py tests/test_gesture_mapper_collisions.py tests/test_landmark_fallback.py tests/test_filters_confidence.py tests/test_filters_drop_none.py tests/test_filters_stability.py tests/test_filters_cooldown.py tests/test_filters_frame_boundary.py tests/test_operator_mock.py tests/test_regression_manifest_schema.py tests/test_recording_scaffold.py tests/test_regression_media.py` - passed: 140 passed, 21 skipped.
- `python3 scripts/mediapipe/check_regression_media.py` - passed; reported 21 missing clips and 19 missing required Phase 5 clips.
- `python3 scripts/mediapipe/check_regression_media.py --strict` - expected failure; reported 19 missing required Phase 5 clips.
- `python3 -m ruff check src tests core camera perception demos scripts` - passed.
- `git diff --check` - passed.

Problems found:
- HIGH: Many important project files are untracked, including active MediaPipeline source/tests/docs/scripts and model/test-media scaffolding. This makes deletion or archiving risky until the user decides what should be committed, ignored, or archived.
- MEDIUM: `data/mediapipe/models/gesture_recognizer.task.sha256` is untracked even though current docs describe the checksum as stored with the model workflow.
- MEDIUM: `docs/known_issues.md` says there is no multi-frame smoothing/debounce yet, but `perception/filters.py` and tests now include stability and cooldown filters.
- LOW: `scripts/mediapipe/diagnose_gesture_channel_order.py` appears useful but is undocumented and untracked.
- LOW: README roadmap still lists "Gesture input through MediaPipe Hands" as a later possibility, which may be stale now that the MediaPipeline gesture layer exists.
- LOW: Ignored generated files are present locally (`.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `src/dume.egg-info/`, `.vscode/`); they are not a repository-tracking problem.
- LOW: `tests/test_drop_none_filter.py` and `tests/test_filters_drop_none.py` have overlapping names that may confuse future contributors.

Recommended staged cleanup plan:
Stage 1 — Safe mechanical cleanup:
- Locally remove ignored cache/build/IDE artifacts if desired: `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `src/dume.egg-info/`, `.vscode/browse.vc.db*`.
- Keep `.gitignore` as-is for the observed generated files; it already ignores the relevant cache/build/editor paths.
- Decide whether `.claude/settings.local.json` should also be project-ignored despite being covered by the user's global git ignore.

Stage 2 — Documentation/RAG consolidation:
- Keep canonical current MediaPipeline docs in place.
- Update or archive `docs/known_issues.md` after confirming which RealSense/ABKO issues remain true.
- Remove or clarify stale README roadmap wording about future gesture input.
- Consider adding `docs/archive/README.md` before moving any historical notes.
- Do not mark Phase 5 PASS until required clips exist.

Stage 3 — Test/script organization:
- Document `scripts/mediapipe/diagnose_gesture_channel_order.py` or move it under a future diagnostics section after user approval.
- Review drop-NONE test naming and decide whether both files should remain separate.
- Keep regression-media tests and manifest tests in place.

Stage 4 — Package/module reorganization, if needed:
- No package/module reorganization is recommended now.
- Any future reorganization must preserve `core`, `camera`, and `perception` import boundaries and update tests/imports in the same change.

Stage 5 — Data/media organization:
- Decide whether `data/mediapipe/models/gesture_recognizer.task` should remain local-only or be tracked as an artifact.
- Decide whether `data/mediapipe/models/gesture_recognizer.task.sha256` should be committed.
- Keep real clips out of cleanup decisions until the recording plan is executed.
- Do not add fake recorded media.

User decisions needed:
- Should the model binary be tracked, stored externally, or local-only?
- Should `data/mediapipe/models/gesture_recognizer.task.sha256` be committed?
- Should `docs/known_issues.md` be updated in place, archived, or kept as current?
- Should `scripts/mediapipe/diagnose_gesture_channel_order.py` be documented and kept?
- Should ignored local cache/IDE artifacts be removed from the workspace now?
- Should `.claude/` be added to project `.gitignore` for portability beyond the current global ignore?

Final recommendation:
- The repository is not materially cleaner yet because this was intentionally report-only.
- Additional cleanup should be done in stages after the current MediaPipeline changes are either committed or explicitly sorted.
- The safest next cleanup step is Stage 1: remove ignored generated/cache artifacts locally, then decide the tracking policy for `data/mediapipe/models/gesture_recognizer.task.sha256` and the model artifact.

## Stage 1 Follow-Up — Safe Mechanical Cleanup

Date: 2026-05-08

Scope:
- Performed only safe mechanical cleanup.
- Did not move modules, tests, docs, scripts, configs, models, media, manifests,
  or README files.
- Did not change MediaPipeline behavior.
- Did not create, update, prune, remove, or modify conda environments.

Files changed:
- `.gitignore`
- `docs/repo_organization_audit.md`

Files deleted:
- `.pytest_cache/`
- `.ruff_cache/`
- `src/dume.egg-info/`
- `.vscode/browse.vc.db`
- `.vscode/browse.vc.db-shm`
- `.vscode/browse.vc.db-wal`
- `scripts/__pycache__/`
- `tests/__pycache__/`
- `core/__pycache__/`
- `demos/__pycache__/`
- `perception/__pycache__/`
- `camera/__pycache__/`
- `src/dume/control/__pycache__/`
- `src/dume/__pycache__/`

`.gitignore` changes:
- Replaced blanket `.vscode/` ignore with local generated paths:
  `.vscode/browse.vc.db*` and `.vscode/ipch/`.
- Added local runtime/output/temp ignores: `outputs/`, `recordings/`, `tmp/`,
  and `temp/`.
- Added local secret ignores: `.env`, `.env.*`, with `!.env.example` preserved.
- Added local agent/tool-state ignores: `.claude/settings.local.json`,
  `.codex/`, and `.agents/`.
- Existing cache/build ignores already covered `.venv/`, `.pytest_cache/`,
  `.ruff_cache/`, `__pycache__/`, and `*.egg-info/`.
- Existing log rules still ignore `logs/*` while preserving `logs/.gitkeep`.

README command wording changes:
- Inspected only; no Stage 1 README patch was needed.
- README already used `python -m pip`, `python -m pytest`, `python scripts/...`,
  and `python demos/...`.
- Phase 5 remains `PARTIAL PASS`.
- Strict media checks remain documented as expected to fail until required clips
  are recorded.

Files intentionally left unchanged:
- `.venv/`
- `.git/`
- `.vscode/settings.json`
- `.vscode/c_cpp_properties.json`
- `.claude/settings.local.json`
- `.codex/`
- `.agents/`
- `data/mediapipe/models/gesture_recognizer.task`
- `data/mediapipe/models/gesture_recognizer.task.sha256`
- Source, tests, scripts, docs, configs, README files, media scaffolds, and
  manifests.

Model/checksum status:
- `data/mediapipe/models/gesture_recognizer.task` is present and untracked.
- `data/mediapipe/models/gesture_recognizer.task.sha256` is present and untracked.
- Tracking/storage policy for these files was not decided in this pass.

Checks run:
- `git status --short --branch` - recorded.
- `.gitignore` coverage checked with `git check-ignore`.
- Safe deletion candidates verified absent outside `.venv/`.
- `git diff --check` - passed.

Expected failures:
- Strict regression media validation was not run in this Stage 1 pass.
- It remains expected to fail until required Phase 5 clips are recorded.

Remaining decisions:
- Decide whether to commit `.vscode/settings.json` and
  `.vscode/c_cpp_properties.json`, now that blanket `.vscode/` ignore was
  removed.
- Decide model/checksum tracking or external artifact policy.
- Create or provide the canonical `dume` conda environment later only when
  environment changes are explicitly allowed.

## Stage 2 Follow-Up — Documentation And Media Validation Consolidation

Date: 2026-05-08

Scope:
- Performed documentation/media validation consolidation only.
- Did not move modules, tests, scripts, configs, models, media, manifests, or
  README files.
- Did not change MediaPipeline behavior.
- Did not create, update, prune, remove, or modify conda environments.

Files changed:
- `docs/validation/README.md`
- `docs/TECHNICAL.md`
- `docs/mediapipeline/current_state.md`
- `docs/mediapipeline/recording_plan.md`
- `docs/mediapipeline/build_plan_v5.md`
- `docs/mediapipeline/phase_verification_checklist.md`
- `data/mediapipe/regression_media/README.md`
- `docs/repo_organization_audit.md`

Docs updated:
- Added `docs/validation/README.md` as a short validation command index.
- Linked `docs/TECHNICAL.md` to the validation index.
- Clarified that `scripts/mediapipe/diagnose_gesture_channel_order.py` is diagnostic only,
  useful for camera/channel-order and MediaPipe canned-label debugging, and not
  part of normal validation.
- Clarified document ownership:
  - `README.md` is the human overview.
  - `docs/TECHNICAL.md` is the canonical agent/developer RAG guide.
  - `docs/validation/README.md` is the validation command index.
  - `docs/mediapipeline/current_state.md` is current MediaPipeline status.
  - `docs/mediapipeline/recording_plan.md` is the required-clip capture plan.
  - `docs/mediapipeline/phase_verification_checklist.md` is the phase checklist.
  - `data/mediapipe/regression_media/README.md` is directory-specific media guidance.

Validation docs added:
- `docs/validation/README.md`

Stale claims corrected:
- Updated remaining MediaPipeline validation command examples from `python3` to
  activated-environment `python` command forms.
- Clarified that strict media validation failure is expected while required
  primary clips are missing.
- Added explicit warnings not to add fake media or mark missing clips present.
- Clarified that Phase 4 stability/cooldown filters exist, while
  camera-specific RealSense/ABKO reliability still requires real hardware/media
  validation.
- Manual webcam and RealSense validation remain documented as outstanding unless
  explicitly recorded.
- Phase 5 remains `PARTIAL PASS`.

Files intentionally left unchanged:
- `README.md` remained in place as the human-facing overview.
- Existing MediaPipeline docs were not moved or merged.
- `scripts/mediapipe/diagnose_gesture_channel_order.py` was not moved.
- `data/mediapipe/regression_media/manifest.json` was not changed.
- Model files, checksum files, media files, source, tests, scripts, configs, and
  conda environments were not changed.

Checks run:
- `git status --short --branch` - recorded.
- Documentation consistency checked with `rg`.
- `git diff --check` - passed.

Remaining decisions:
- Decide whether `scripts/mediapipe/diagnose_gesture_channel_order.py` should stay as a
  normal script, move later into a diagnostics namespace, or become documented
  in README only if it becomes a common user workflow.
- Decide model/checksum tracking or external artifact policy.
- Capture required real primary clips before Phase 5 can become PASS.

## Stage 3 Follow-Up — Model And Checksum Policy Validation

Date: 2026-05-08

Scope:
- Validated model/checksum state and documented policy only.
- Did not modify model binary contents.
- Did not delete the model or checksum.
- Did not run `git add`, commit, or otherwise change git tracking.
- Did not change runtime or MediaPipeline behavior.
- Did not edit regression media manifests or recorded clip status.
- Did not create, update, prune, remove, or modify conda environments.

Files changed:
- `README.md`
- `docs/TECHNICAL.md`
- `docs/validation/README.md`
- `docs/mediapipeline/phase_verification_checklist.md`
- `docs/repo_organization_audit.md`

Model binary status:
- Path: `data/mediapipe/models/gesture_recognizer.task`
- Exists: yes.
- Size: 8,373,440 bytes.
- Git status: untracked.
- Ignore status: not ignored by project `.gitignore`.
- Policy recommendation: keep local/external; do not add to normal git history.

Checksum status:
- Path: `data/mediapipe/models/gesture_recognizer.task.sha256`
- Exists: yes.
- Size: 65 bytes.
- Git status: untracked.
- Ignore status: not ignored by project `.gitignore`.
- Policy recommendation: track this file in git.

SHA-256 verification result:
- Computed model SHA-256:
  `97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482`
- Checksum file value:
  `97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482`
- Result: match.

Recommended model/checksum policy:
- Option B — track checksum only, keep model binary external/local.
- Rationale: `scripts/mediapipe/download_gesture_model.py` can recreate the model from the
  pinned upstream URL and verify it against the checksum. Runtime code does not
  download the model automatically; missing model setup fails clearly with
  instructions.
- If accepted, add later:
  - `data/mediapipe/models/gesture_recognizer.task.sha256`
- Do not add later unless the owner explicitly chooses normal git or Git LFS:
  - `data/mediapipe/models/gesture_recognizer.task`
- A later cleanup pass may add an ignore rule for the local model binary while
  keeping the checksum visible, if the owner accepts this policy.

Files intentionally left unchanged:
- `data/mediapipe/models/gesture_recognizer.task`
- `data/mediapipe/models/gesture_recognizer.task.sha256`
- `data/mediapipe/regression_media/manifest.json`
- Model, media, manifests, source, tests, scripts, configs, and conda
  environments.

Checks run:
- `git status --short --branch` - recorded.
- `ls -l data/mediapipe/models/gesture_recognizer.task data/mediapipe/models/gesture_recognizer.task.sha256`
- `git status --short data/mediapipe/models/gesture_recognizer.task data/mediapipe/models/gesture_recognizer.task.sha256`
- `git ls-files data/mediapipe/models/gesture_recognizer.task data/mediapipe/models/gesture_recognizer.task.sha256`
- `git check-ignore -v -- data/mediapipe/models/gesture_recognizer.task data/mediapipe/models/gesture_recognizer.task.sha256`
- `sha256sum data/mediapipe/models/gesture_recognizer.task`
- `cat data/mediapipe/models/gesture_recognizer.task.sha256`
- Reference scans with `rg`.
- `git diff --check` - passed.

Remaining decisions:
- Owner approval to track `data/mediapipe/models/gesture_recognizer.task.sha256`.
- Owner approval for whether to ignore `data/mediapipe/models/gesture_recognizer.task` in
  a later `.gitignore` pass.
- Whether model binary versioning should ever use Git LFS or external artifact
  storage instead of local download.

## Stage 4 Follow-Up — Script And Test Organization

Date: 2026-05-08

Scope:
- Reviewed script and test organization only.
- Did not move, rename, or delete scripts or tests.
- Did not reorganize production modules.
- Did not change runtime or MediaPipeline behavior.
- Did not change regression media, model binary contents, manifests, configs, or
  conda environments.

Files changed:
- `docs/repo_organization_audit.md`

Model/checksum policy state:
- `data/mediapipe/models/gesture_recognizer.task` is ignored by project `.gitignore` and
  remains a local/external artifact.
- `data/mediapipe/models/gesture_recognizer.task.sha256` is not ignored and remains
  visible for future tracking.
- `git status --short --untracked-files=all data/mediapipe/models` reports only
  `data/mediapipe/models/gesture_recognizer.task.sha256` as untracked.

Scripts reviewed:
- `scripts/mediapipe/download_gesture_model.py` remains the setup/verification path for
  the local MediaPipe model. Runtime code must not download the model
  automatically.
- `scripts/mediapipe/check_regression_media.py` remains the hardware-free manifest/media
  status checker. Strict mode is expected to fail while required primary clips
  are missing.
- `scripts/mediapipe/record_regression_clip.py` remains the real-media recording scaffold.
  It should not be treated as normal validation.
- `scripts/mediapipe/diagnose_gesture_channel_order.py` remains diagnostic only for
  camera channel-order and canned-label debugging. It should not be treated as
  normal validation.

Tests reviewed:
- `tests/test_drop_none_filter.py` is the narrower Phase 2 drop-NONE/event
  conversion coverage.
- `tests/test_filters_drop_none.py` is Phase 4 filter-chain coverage, including
  stability behavior after dropped `NONE` observations.
- The two files have overlapping names but different phase ownership, so they
  were left unchanged.

Files intentionally left unchanged:
- `scripts/mediapipe/check_regression_media.py`
- `scripts/mediapipe/diagnose_gesture_channel_order.py`
- `scripts/mediapipe/download_gesture_model.py`
- `scripts/mediapipe/record_regression_clip.py`
- `tests/test_drop_none_filter.py`
- `tests/test_filters_drop_none.py`
- `data/mediapipe/models/gesture_recognizer.task`
- `data/mediapipe/models/gesture_recognizer.task.sha256`
- Source, tests, scripts, docs other than this audit note, configs, models,
  media, manifests, and conda environments.

Checks run:
- `git status --short --branch` - recorded.
- `git check-ignore -v data/mediapipe/models/gesture_recognizer.task` - confirmed ignored
  by `.gitignore`.
- `git check-ignore -v data/mediapipe/models/gesture_recognizer.task.sha256 || true` -
  confirmed no ignore rule matched.
- `git status --short --untracked-files=all data/mediapipe/models` - reported only the
  checksum as untracked.
- Reference scans with `rg`.
- `python -m pytest ...` - not run because `python` is not available on PATH in
  this shell.
- `python3 -m pytest -q -p no:cacheprovider tests/test_drop_none_filter.py
  tests/test_filters_drop_none.py tests/test_recording_scaffold.py
  tests/test_regression_manifest_schema.py` - passed: 18 passed.
- `python3 -m ruff check --no-cache scripts tests/test_drop_none_filter.py
  tests/test_filters_drop_none.py tests/test_recording_scaffold.py
  tests/test_regression_manifest_schema.py` - passed.
- `git diff --check` - passed.

Remaining decisions:
- Track `data/mediapipe/models/gesture_recognizer.task.sha256` when the owner is ready to
  add project files.
- Decide later whether the diagnostic script should stay in `scripts/` or move
  into a diagnostics namespace; do not move it without updating references.
- Decide later whether the Phase 2 and Phase 4 drop-NONE test names should be
  clarified. Current behavior and phase ownership are valid.

## Stage 5 Follow-Up — Light Docs And File Organization Planning

Date: 2026-05-08

Scope:
- Reviewed documentation and top-level file organization only.
- Did not move, rename, archive, or delete files.
- Did not reorganize production modules or change import paths.
- Did not change runtime or MediaPipeline behavior.
- Did not change regression media, model binary contents, manifests, configs, or
  conda environments.

Files changed:
- `docs/repo_organization_audit.md`

Phase checklist patch result:
- No checklist patch was needed. `docs/mediapipeline/phase_verification_checklist.md`
  already says recorded-media regression tests must run against required
  primary clips and pass within accepted thresholds, and that documented
  failures keep Phase 5 at `FAIL` or `PARTIAL PASS`.
- Phase 5 remains `PARTIAL PASS` while required primary clips are missing.

Docs organization result:
- `README.md`: current/canonical human overview; do not move.
- `docs/TECHNICAL.md`: current/canonical agent/developer RAG guide; do not move.
- `docs/validation/README.md`: validation/index; do not move.
- `docs/known_issues.md`: current issue reference; do not move. Candidate for
  archive later only after RealSense/ABKO status is resolved or superseded.
- `docs/mediapipeline/current_state.md`: current/canonical MediaPipeline status;
  do not move.
- `docs/mediapipeline/recording_plan.md`: current MediaPipeline recording plan;
  do not move.
- `docs/mediapipeline/build_plan_v5.md`: planning/reference document still
  referenced by the checklist; do not move now. Candidate for archive later only
  after current docs fully supersede it and references are updated.
- `docs/mediapipeline/phase_verification_checklist.md`: active phase checklist;
  do not move.
- `docs/CREATION_LOG.md`: historical/reference project memory; do not move now.
  Candidate for archive later if a docs history area is explicitly approved.
- `docs/repo_organization_audit.md`: active cleanup history and staged plan; do
  not move while cleanup is ongoing.
- `data/mediapipe/regression_media/README.md`: directory-specific current media instructions;
  do not move.
- `data/motions/README.md`: directory-specific current motion instructions; do
  not move.

Archive decision:
- `docs/archive/` was not created. No document is clearly obsolete enough to
  archive in this pass without losing current references or useful project
  memory.

File organization result:
- `core/`: keep current for now; risky to move because it owns shared
  MediaPipeline contracts and import-boundary tests depend on this path.
- `camera/`: keep current for now; risky to move because demos/tests import it
  directly and boundary rules depend on this layout.
- `perception/`: keep current for now; risky to move because gesture/filter
  tests and demos import it directly.
- `src/dume/`: keep current for now; risky to move because `pyproject.toml`
  package discovery and the `dume` CLI entrypoint depend on it.
- `tests/`: keep current for now; moving would require pytest and reference
  updates.
- `scripts/`: keep current for now; moving would require README/docs/test
  reference updates.
- `demos/`: keep current for now; moving would require README/docs updates.
- `data/`: keep current for now; model, manifest, media, poses, and motion paths
  are documented and tested.
- `config/`: keep current for now; runtime config paths are part of the project
  scaffold.
- `logs/`: keep current for now; `logs/.gitkeep` preserves the directory while
  `logs/*` remains ignored.

`.vscode` project settings decision status:
- `.vscode/settings.json` contains ROS/Jazzy and absolute Python analysis paths.
  It is machine-specific or owner-workspace-specific and needs user decision
  before tracking.
- `.vscode/c_cpp_properties.json` contains ROS/Jazzy include paths plus system
  compiler settings. It may be useful for this workspace, but it is not clearly
  portable DUM-E project config and needs user decision before tracking.
- Neither file is ignored by project `.gitignore` after Stage 1.

Remaining untracked/track-later policy:
- `data/mediapipe/models/gesture_recognizer.task.sha256` should be tracked later if the
  owner approves.
- `data/mediapipe/models/gesture_recognizer.task` should remain ignored/local.
- `.vscode` project settings need owner decision.
- `environment.yml` defines the clean-machine `dume` environment and is
  currently untracked. It should be tracked later if the owner approves because
  it defines the canonical clean-machine conda environment.
- `conda info --envs` shows `base`, `dume-media`, and `lerobot`, but no `dume`
  environment in this workspace. The canonical `dume` conda environment still
  needs creation later when environment changes are explicitly allowed.

Files intentionally left unchanged:
- `README.md`
- `docs/TECHNICAL.md`
- `docs/validation/README.md`
- `docs/known_issues.md`
- `docs/mediapipeline/current_state.md`
- `docs/mediapipeline/recording_plan.md`
- `docs/mediapipeline/build_plan_v5.md`
- `docs/mediapipeline/phase_verification_checklist.md`
- `docs/CREATION_LOG.md`
- `data/mediapipe/regression_media/README.md`
- `data/motions/README.md`
- `.vscode/settings.json`
- `.vscode/c_cpp_properties.json`
- `data/mediapipe/models/gesture_recognizer.task`
- `data/mediapipe/models/gesture_recognizer.task.sha256`
- Source, tests, scripts, configs, models, media, manifests, and conda
  environments.

Checks run:
- `git status --short --branch` - recorded.
- Documentation and reference scans with `rg`.
- `.vscode` settings inspected.
- Top-level directory layout inspected with `find`.
- `conda info --envs` - read-only environment inventory; no conda changes made.
- `python3 -m pytest -q tests/test_readme_commands.py` - passed: 1 passed.
- `python3 -m pytest -q tests/test_import_boundaries.py` - passed: 4 passed.
- `python3 -m ruff check src tests core camera perception demos scripts` -
  passed.
- `git diff --check` - passed.

Remaining decisions:
- Track `environment.yml` when the owner is ready to add project files, because
  it defines the canonical clean-machine `dume` conda environment.
- Decide whether to track `data/mediapipe/models/gesture_recognizer.task.sha256`.
- Decide whether `.vscode/settings.json` and `.vscode/c_cpp_properties.json`
  are project settings or local-only owner settings.
- Decide later whether `docs/CREATION_LOG.md` or
  `docs/mediapipeline/build_plan_v5.md` should move to an archive/history area
  after active references are updated.

## Stage 6 Follow-Up — Feature-Lane Repository Organization

Date: 2026-05-11

Scope:
- Organized assets, scripts, and documentation into manual-reading, MediaPipe,
  MediaPipeline, and LeRobot lanes.
- Did not add new runtime functionality.
- Did not delete files.
- Did not move generic perception code.
- Preserved `core`, `camera`, and `perception` import boundaries.

Files and folders moved:
- Root manual reference images `manual2-c1.jpg` through `manual2-c5.jpg` moved
  to `data/manuals/raw/`.
- `data/manuals/.gitkeep` moved to `data/manuals/processed/.gitkeep`.
- `data/models/gesture_recognizer.task.sha256` moved to
  `data/mediapipe/models/gesture_recognizer.task.sha256`.
- Local ignored `data/models/gesture_recognizer.task` moved to
  `data/mediapipe/models/gesture_recognizer.task`.
- `data/test_media/README.md` and `data/test_media/manifest.json` moved to
  `data/mediapipe/regression_media/`.
- MediaPipe scripts moved to `scripts/mediapipe/`.
- MediaPipeline docs moved to `docs/mediapipeline/` and renamed to
  `build_plan_v5.md`, `current_state.md`, `phase_verification_checklist.md`,
  and `recording_plan.md`.
- `camera/lerobot_adapter.py` moved to
  `src/dume/integrations/lerobot/camera_adapter.py`.

Placeholder folders/files added:
- Manual data: `data/manuals/README.md`, `data/manuals/extracted/.gitkeep`,
  and `data/manuals/annotations/.gitkeep`.
- MediaPipe data: `data/mediapipe/README.md` and
  `data/mediapipe/diagnostics/README.md`.
- LeRobot data: `data/lerobot/README.md` plus `.gitkeep` placeholders under
  `datasets/`, `episodes/`, `policies/`, and `calibration/`.
- Documentation lanes: `docs/manuals/README.md`, `docs/mediapipe/README.md`,
  and `docs/lerobot/README.md`.
- Script lanes: `scripts/manuals/README.md` and `scripts/lerobot/README.md`.
- Integration lane: `src/dume/integrations/__init__.py`,
  `src/dume/integrations/lerobot/__init__.py`, and
  `src/dume/integrations/lerobot/README.md`.

Path/reference updates:
- Updated README, docs, tests, demos, scripts, and perception defaults from
  `data/models/` to `data/mediapipe/models/`.
- Updated regression media references from `data/test_media/` to
  `data/mediapipe/regression_media/`.
- Updated script references from `scripts/*.py` to `scripts/mediapipe/*.py`.
- Updated MediaPipeline doc links from `docs/mediapipeline_*.md` to
  `docs/mediapipeline/*.md`.
- Updated tests to import moved scripts from `scripts.mediapipe`.
- Updated the camera factory to lazily load the moved LeRobot placeholder
  adapter only for `backend="lerobot"`.

`.gitignore` updates:
- Ignored `data/mediapipe/models/gesture_recognizer.task`.
- Ignored generated contents under `data/mediapipe/diagnostics/` while keeping
  `data/mediapipe/diagnostics/README.md` trackable.
- Ignored `.claude/`, `.codex/`, and `.agents/`.
- Kept checksum and regression manifest/README files trackable.

Checks run:
- `python -m pytest` - not available because `python` is not on PATH.
- `python3 -m pytest` - passed: 159 passed, 21 skipped.
- `python -m ruff check .` - not available because `python` is not on PATH.
- `python3 -m ruff check .` - passed.
- `python3 scripts/mediapipe/check_regression_media.py` - passed; reported 21
  missing clips and 19 missing required Phase 5 clips.
- `git diff --check` - passed.

Skipped moves:
- Generic perception modules were not moved because asset/doc/script
  organization was the priority and the existing imports are stable.

## Stage 7 Follow-Up — RAG And Documentation Refresh

Date: 2026-05-11

Scope:
- Updated current RAG, technical, validation, and feature-lane documentation to
  reflect the organized repository layout.
- Did not change runtime behavior.
- Did not delete files.

Files updated:
- `docs/TECHNICAL.md`
- `README.md`
- `docs/validation/README.md`
- `docs/CREATION_LOG.md`
- `docs/known_issues.md`
- `docs/manuals/README.md`
- `docs/mediapipe/README.md`
- `docs/lerobot/README.md`
- `data/manuals/README.md`
- `data/mediapipe/README.md`
- `data/lerobot/README.md`
- `scripts/manuals/README.md`
- `scripts/lerobot/README.md`
- `src/dume/integrations/lerobot/README.md`
- `docs/mediapipeline/build_plan_v5.md`
- `docs/mediapipeline/current_state.md`
- `docs/mediapipeline/phase_verification_checklist.md`
- `docs/mediapipeline/recording_plan.md`
- `docs/mediapipeline_phase_verification_checklist.md`

Documentation result:
- `docs/TECHNICAL.md` now identifies the feature lanes and is dated
  2026-05-11.
- README now includes the documentation map and lane boundary rule.
- Validation docs now include organization checks and current canonical paths.
- Feature-lane READMEs now state what belongs in manual-reading, MediaPipe, and
  LeRobot areas.
- The legacy `docs/mediapipeline_phase_verification_checklist.md` path is kept
  as a compatibility copy and points readers to the canonical
  `docs/mediapipeline/phase_verification_checklist.md`.

Checks run:
- Stale-reference scans with `rg`.
- `git diff --check` - pending in this pass until validation completes.
