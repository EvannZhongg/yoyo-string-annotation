---
name: yoyo-string-annotation
description: Build high-quality yoyo string annotation collections by having a vision-capable agent directly inspect, annotate, repeatedly refine, self-review, audit, and export labels without detector, segmentation, pose, SAM, or other recognition-model prelabels. Use for dispersed video frame sampling, thin-string centerlines or masks, normal-versus-horizontal trick orientation, ordered hand-to-yoyo path continuity, adjacent-frame refinement, hard negatives, unresolved-case handling, and source-group-preserving annotation production before any later dataset split.
---

# Agent Yoyo String Annotation

Create evidence-bound string labels with direct agent vision. Never bootstrap
geometry from a recognition model. Keep the skill self-contained; write only
source-derived frames, annotation projects, review renders, and exports outside
the skill directory.

## Load the needed references

- Read `references/data-contract.md` before creating a dataset or export.
- Read `references/annotation-schema.md` before writing candidate JSON.
- Read `references/sampling-protocol.md` before sampling video.
- Read `references/review-protocol.md` before revising or approving labels.

Use `scripts/annotation_pipeline.py` for every label state change. Do not
hand-edit digests, normalized coordinate mirrors, approval status, or revision
history.

## Prohibit recognition prelabels

Do not run a detector, segmenter, pose estimator, SAM-like model, trained tracker,
or existing annotation model to create or choose label geometry. Do not import
host-project code or weights. A vision-capable agent must inspect source pixels
and author the initial candidate itself.

Allowed deterministic aids are coordinate grids, crops, contrast-preserving
renders, image hashes, non-semantic appearance descriptors for sampling, and
optical flow from an agent-reviewed adjacent frame. Treat optical flow only as a
pending seed and confirm every retained edge against the current raw frame.

## Sample dispersed video evidence

Create source-balanced anchors across the whole duration of every video. The
sampler uses temporal strata and low-resolution appearance distance only; it
does not locate a yoyo or string.

```bash
python "$SKILL_DIR/scripts/sample_video_frames.py" \
  --videos INPUT_VIDEOS --output PROJECT \
  --frames-per-video 12 --oversample-factor 5 \
  --neighbor-offsets=-2,-1,1,2
```

Inspect `anchor_contact_sheet.jpg` and the raw extracted frames. Preserve each
video identity in `source_group`. Keep `sampling_manifest.json`; it is the
script-authoritative mapping from every extracted image to its source video,
video SHA-256, frame index, and timestamp. Retain anchors spanning different
times and visible formations; use nearby context frames for continuity, not as
substitutes for scene diversity.

Initialize the annotation project:

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" init \
  --images PROJECT/images --output PROJECT --min-approvals 2
```

`init` auto-discovers `PROJECT/sampling_manifest.json`; pass
`--sampling-manifest PATH` when it is elsewhere. Initialization must fail when
an image has no unique manifest record or its hash/source group differs. The
pipeline copies provenance into every label.

Do not assign `train`, `val`, or `test` here. Keep all frames from a source video
under the same `source_group`; a downstream dataset-building step may later
perform source-isolated partitioning.

## Annotate directly and refine repeatedly

For every anchor, inspect the full-resolution raw image and a coordinate grid.
Write a complete candidate JSON using the annotation schema. Put only visible,
current-frame rope pixels in `string_polylines_pixel` or masks. Preserve the
ordered route and hidden gaps separately in `string_path`. Classify each trick
as `trick_orientation=normal` or `horizontal` from the launch motion in nearby
frames; do not infer horizontal play from one horizontal string segment.

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" apply \
  --label LABEL.json --candidate CANDIDATE.json \
  --actor agent-annotator --role model-annotator --model AGENT_ID \
  --message "direct current-frame annotation"

python "$SKILL_DIR/scripts/annotation_pipeline.py" render \
  --label LABEL.json --output REVIEW_DIR
```

Open the raw, `*_grid.jpg`, `*_overlay.jpg`, and `*_detail.jpg`. Move individual
points, add bends, split strokes at occlusions, remove unsupported edges, and
reapply the entire corrected candidate. Render again after every revision.
Continue this loop without an arbitrary revision limit until every visible edge
tracks the depicted string or the frame is declared unresolved.

Never connect endpoints merely to make a smooth loop or closed shape. A long
straight edge is valid only when pixels support its full length. Keep observed
segments separate across occlusion and record the gap in `string_path`.

## Refine adjacent frames

Annotate and approve an anchor before using it as a temporal source. For a close
neighbor, propagate the approved geometry, then make small current-frame edits:

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" propagate \
  --previous-label APPROVED.json --target-label NEIGHBOR.json \
  --actor agent-temporal-seed --model AGENT_ID
```

Propagation never approves a label. Inspect the neighbor raw image and rendered
detail, delete failed tracks, split new occlusions, add newly visible pieces,
and change an edge from `temporal` to `observed` only after pixel confirmation.
If propagation loses the string or the interval is too large, discard the seed
and annotate directly.

## Self-review and abandon unsafe cases

Run at least two digest-bound review passes with distinct roles. The geometry
critic checks every consecutive edge at detail scale. The semantic/temporal
critic independently checks visibility, anchors, topology, variation tags,
negatives, `trick_orientation`, and neighboring frames. For a trick, reopen a
short temporal window and verify the throw plane before semantic approval.

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" review \
  --label LABEL.json --decision approve \
  --reviewer agent-geometry-pass --role geometry-critic \
  --model AGENT_ID --notes "edge-by-edge pixel findings"

python "$SKILL_DIR/scripts/annotation_pipeline.py" review \
  --label LABEL.json --decision approve \
  --reviewer agent-semantic-pass --role semantic-critic \
  --model AGENT_ID --notes "independent visibility and continuity findings"
```

Use `request_changes` and repeat the apply/render/review loop whenever a defect
remains. Any edit invalidates earlier approvals. If blur, occlusion, ambiguity,
or repeated failed refinement prevents a defensible label, record an
`unresolved` decision with factual notes. Unresolved and rejected items remain
auditable but are excluded from export.

## Audit and export

Run strict audit before export. A final annotation delivery may require every
record to be approved; a working project may retain unresolved records:

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" audit \
  --labels PROJECT/labels --output PROJECT/audit.json --strict

python "$SKILL_DIR/scripts/annotation_pipeline.py" export \
  --labels PROJECT/labels --output REVIEWED_EXPORT
```

Export creates a portable snapshot containing copied original frames, reviewed
label JSON, terminal annotation overlays, and a manifest. Each label references
its matching visualization under `visualizations/<source_group>/`, and the
manifest records the overlay SHA-256 plus per-frame and per-video provenance.
Inspect excluded counts, source identity, visibility coverage, and variation
tags before handing the collection to a separate dataset-partitioning step.

If rendering rules change after export, refresh the terminal overlays and
manifest digests without changing labels or source frames:

```bash
python "$SKILL_DIR/scripts/annotation_pipeline.py" refresh-visualizations \
  --export REVIEWED_EXPORT
```

## Verify the skill

After changing any skill resource, run:

```bash
python "$SKILL_DIR/scripts/self_test.py"
```

Run the standalone complex-scene acceptance suite after workflow or gate changes:

```bash
python "$SKILL_DIR/scripts/acceptance_suite.py" --output EMPTY_ACCEPTANCE_DIR
```

Require at least ten terminal cases, zero pending/failed cases, a passing
collection audit, and exactly documented exclusions for unresolved scenes. Keep
run-specific dates, counts, findings, and reports with the generated project,
not in the skill Markdown.
