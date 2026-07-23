# Annotation Data Contract

## Consumer requirements

The target is thin binary string segmentation. This skill produces reviewed
current-frame geometry and explicit negative states while preserving source
identity. Dataset partitioning is deliberately outside its scope.

Required top-level fields:

| Field | Contract |
| --- | --- |
| `source_image` | Image path in the annotation project or portable export |
| `image_sha256` | Identity check for stale or duplicated source pixels |
| `image_size` | Original `[width,height]` |
| `source_group` | Stable video/source identity for later partitioning |
| `trick_orientation` | `normal`, `horizontal`, `unknown`, or `not_applicable` |
| `string_visibility` | `visible`, `partial`, `not_visible`, or `uncertain` |
| `string_polylines_pixel` | Separate visible centerline strokes |
| `string_mask_polygons_pixel` | Optional visible rope-area polygons |
| `string_review_status` | Only `approved` or `reviewed` may enter a downstream collection |

Pixel geometry is authoritative. Normalized `*_2d` coordinates are generated
mirrors on a 0-999 scale. Consumers may rasterize a reviewed centerline with a
small configured width when no mask exists. `not_visible` is a reviewed empty
mask. Exclude `uncertain`, `unresolved`, `rejected`, and pending labels.

## Continuity metadata

`string_path` stores ordered paths and per-edge evidence. It supports topology,
adjacent-frame refinement, and QA, but `temporal` and `inferred` edges must never
be rasterized into segmentation truth. `observed` edges must also be represented
by current-frame visible geometry.

`yoyo_bbox_pixel`, `hands_pixel`, `string_attachment_class`, `scene_label`,
`trick_orientation`, and `variation_tags` are review and stratification
metadata. They are not permission to draw a string between objects. Approved
trick records must use `normal` or `horizontal`; approved non-trick records use
`not_applicable`.

## Portable export

The exporter writes original frames under `images/<source_group>/`, matching
labels under `labels/<source_group>/`, terminal annotation overlays under
`visualizations/<source_group>/`, and `manifest.json`. Exported `source_image` and
`visualization` paths are relative to each label; `source_image_original`
preserves provenance. The manifest records every overlay SHA-256 so stale or
mismatched visualizations can be detected. No consumer-specific module,
repository path, weights path, or import is embedded in the skill.

The annotation schema contains no `split` field. A later consumer must partition
whole `source_group` values atomically and must not infer a partition from folder
names created by this skill.

Visible centerlines are rendered as translucent cyan strokes with hollow blue
control points. This keeps the underlying source pixels visible for direct
alignment review. Temporal edges are orange and inferred edges are dashed
magenta; neither is presented as current-frame segmentation truth.
