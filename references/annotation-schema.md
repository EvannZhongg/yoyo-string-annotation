# Annotation Schema

## Script-owned provenance

Every label uses schema `agent_yoyo_string_annotation_v3` and carries
`source_video`, `source_video_sha256`, `source_group`, `video_id`, `frame_index`,
`timestamp_s`, `sequence_id`, `sampling_role`, `anchor_frame_index`, and
`sampling_manifest_sha256`. `annotation_pipeline.py init` copies these fields
from the sampling manifest.

## Coordinates and visible geometry

Use original image pixels as `[x,y]` from the upper-left. Add points at bends,
crossings, and curvature changes. Split strokes at occlusions or unresolved
crossings. Do not bridge a gap for visual neatness.

For a one-to-three-pixel string, prefer centerlines. Use mask polygons only when
both visible boundaries are defensible. Keep every geometry point inside the
image.

## Complete candidate

Every apply operation supplies the complete current candidate, for example:

```json
{
  "visibility": "visible",
  "yoyo_bbox_pixel": [742, 430, 790, 480],
  "string_visibility": "partial",
  "string_polylines_pixel": [
    [[510, 190], [548, 250], [602, 318]],
    [[635, 340], [700, 397], [754, 440]]
  ],
  "string_mask_polygons_pixel": null,
  "hands_pixel": {"left": [510, 190], "right": null},
  "string_attachment_class": "hand_and_yoyo_attached",
  "scene_label": "trick",
  "trick_orientation": "horizontal",
  "variation_tags": ["occluded", "curved", "multi_segment"],
  "string_path": {
    "topology": "open",
    "reconstruction_status": "partial",
    "paths": [
      {
        "path_id": "left-hand-to-yoyo",
        "start_anchor": "left_hand",
        "end_anchor": "yoyo",
        "points_pixel": [[510,190], [548,250], [602,318], [635,340], [700,397], [754,440]],
        "edges": [
          {"from": 0, "to": 1, "evidence": "observed", "confidence": 0.96},
          {"from": 1, "to": 2, "evidence": "observed", "confidence": 0.94},
          {"from": 2, "to": 3, "evidence": "inferred", "confidence": 0.35},
          {"from": 3, "to": 4, "evidence": "observed", "confidence": 0.91},
          {"from": 4, "to": 5, "evidence": "observed", "confidence": 0.93}
        ]
      }
    ],
    "unresolved_gaps": ["rope is hidden between (602,318) and (635,340)"]
  },
  "bad_case": ["partial_occlusion"],
  "notes": "Two current-frame strokes; hidden gap retained only in path metadata."
}
```

## Visibility

- `visible`: the important visible route can be traced defensibly.
- `partial`: some visible string is defensible, but the current frame cannot
  support every visible/expected section.
- `not_visible`: no string pixels can be defended; retain no geometry.
- `uncertain`: neither a positive nor negative label is defensible.

## Evidence and continuity

Each path edge connects consecutive point indexes and uses `observed`, `temporal`,
or `inferred`. Use `observed` only when the entire edge follows current pixels.
Use `temporal` only for an unconfirmed adjacent-frame seed. Use `inferred` for a
plausible hidden route. Set reconstruction to `complete` only when order and
anchors are unambiguous.

## Trick orientation

Use `trick_orientation` as a frame-level label backed by the surrounding launch
event:

- `horizontal`: the yoyo is thrown laterally, with its initial or dominant
  launch direction clearly near the image horizontal axis. Confirm motion in a
  short neighboring-frame window; a horizontal string segment alone is not
  evidence.
- `normal`: a trick whose launch is clearly not horizontal, including the usual
  downward or predominantly vertical throw plane.
- `unknown`: a draft or unresolved trick for which the launch event is missing,
  occluded, blurred, or ambiguous. A `scene_label=trick` record cannot be
  approved while this value remains unknown.
- `not_applicable`: required for `scene_label=non_trick`.

Keep the label consistent across frames that clearly belong to the same launch
event. Recheck rather than propagating it blindly across an event boundary.

Schema v1 records have no trick orientation. Reapply them as schema v2
candidates and repeat both reviews; do not preserve approvals whose digest did
not bind this field.

Suggested `variation_tags` include `straight`, `curved`, `v_shape`, `loop`,
`crossing`, `branched`, `multi_segment`, `occluded`, `motion_blur`,
`low_contrast`, `edge_clipped`, `small_yoyo`, `no_string`, and `background_edge`.
Tags describe reviewed visual evidence and support downstream stratification.
