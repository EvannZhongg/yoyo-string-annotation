# Iterative Agent Review Protocol

## Direct annotation pass

Inspect the original pixels, never a recognition proposal. Trace all defensible
visible strokes and build an ordered path whose edges state their evidence.
Apply the complete candidate and render all review views.

## Fine-adjustment loop

Repeat until approved or unresolved:

1. Compare raw, grid, overlay, and detail views.
2. Inspect every edge, not merely each control point.
3. Move drifted points onto the string centerline.
4. Add points where a segment cuts a bend.
5. Delete background, motion-trail, clothing, finger, or floor edges.
6. Split a stroke at every unsupported gap or ambiguous crossing.
7. Update anchors, visibility, path ordering, gaps, and variation tags.
8. Reopen nearby frames and verify `trick_orientation` from launch motion, not
   static string angle.
9. Apply the full candidate as a new revision and rerender.

There is no fixed revision limit. Continue while current pixels support a more
accurate result. Each revision changes the content digest and invalidates prior
approvals.

## Independent critics

The geometry critic ignores earlier notes and checks pixel alignment, curvature,
gaps, masks, and shortcut edges. The semantic/temporal critic independently
checks visibility, negative status, attachment claims, topology, ordered route,
variation tags, `scene_label`, `trick_orientation`, and neighbor coherence. Two
distinct roles must approve the same content digest. The required roles are
`geometry-critic` and `semantic-critic`; the semantic review record includes
`trick_orientation` in its review scope.

The same underlying agent may fill both roles only by reopening the raw and
rendered images with the separate objective. Reviewer identities and factual
findings must differ.

## Stop and abandon

Use `request_changes` when a concrete correction remains possible. Use
`unresolved` when blur, occlusion, multiple plausible strings, an indeterminate
crossing, or repeated failed fine adjustment prevents defensible truth. State
the exact reason in review notes. Use `reject` for invalid source data or a frame
outside the requested domain.

Unresolved and rejected records remain in the annotation project and history,
but the exporter excludes them. Never relabel an ambiguous case as
`not_visible` merely to obtain a terminal class.
