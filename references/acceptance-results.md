# Acceptance Results

## Scope

Executed on 2026-07-24 with `scripts/acceptance_suite.py`. The suite generated
15 independent pixel-grounded scenarios without recognition models or host
project imports. Raw and terminal overlay contact sheets were visually inspected
after the deterministic gates passed.

## Scenarios and outcomes

| ID | Scenario | Outcome |
| --- | --- | --- |
| 01 | One-to-two-pixel straight string | Approved |
| 02 | Long route with several deep bends | Approved |
| 03 | Open V formation that must not be closed | Approved |
| 04 | Two visible strokes separated by occlusion | Approved partial |
| 05 | Self-near loop formation | Approved |
| 06 | Yoyo-visible hard negative | Approved negative |
| 07 | Crossing, multi-path topology | Approved |
| 08 | String clipped by image edge | Approved partial |
| 09 | Low-contrast thin string | Approved |
| 10 | Non-trick hard negative | Approved negative |
| 11 | Motion-blurred partial string | Approved partial |
| 12 | Repeated point-level refinement on a clean frame | Approved after three revisions |
| 13 | Strongly blurred, low-contrast double route | Safely unresolved |
| 14 | Reviewed temporal source frame | Approved |
| 15 | Translated adjacent frame | Approved after optical-flow seed and direct correction |

Summary:

- 15 terminal cases, exceeding the required minimum of 10.
- 14 approved labels and 1 explicit unresolved exclusion.
- 0 pending or failed cases.
- Collection audit passed with stable source groups, reviewed positives and
  negatives, varied scenario tags, and digest-bound trick orientations.
- Portable export contained 14 image/label pairs and excluded the unresolved
  case exactly once.
- Temporal propagation tracked 12/12 measurements but remained pending until a
  current-frame revision and two new approvals.

## Defects found and corrected

1. The first open-V fixture assigned its right-hand endpoint to the yoyo. Strict
   anchor distance correctly rejected it; endpoint anchors now derive from
   actual endpoint proximity.
2. Initial acceptance contact sheets captured pre-review pending renders. The
   suite now rerenders every case after its terminal decision.
3. The initial unresolved fixture was visually too clear. It now uses two
   strongly blurred, low-contrast routes for a defensible unresolved outcome.
4. Repeated fine adjustment was not exercised explicitly. The clean-frame
   refinement case now runs displaced, intermediate, and final revisions and proves that an
   approval bound to the intermediate digest becomes stale after the final edit.
5. Trick-plane semantics are now explicit. Approved trick records require
   `normal` or `horizontal`, non-trick records normalize to `not_applicable`,
   semantic reviews include the field in their recorded scope, and overlays show
   it in the header.

## Limits

This suite validates workflow, state transitions, geometry rendering, continuity
handling, source identity, and export behavior against known synthetic pixels.
It is not a numerical real-world accuracy claim. Production acceptance should
add a larger independently double-annotated real-video collection, then let a
separate downstream step create source-isolated dataset partitions.
