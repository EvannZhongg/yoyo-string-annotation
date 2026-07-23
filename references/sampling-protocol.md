# Dispersed Video Sampling Protocol

## Purpose

Build annotation candidates that span sources, time, scene appearance, and
adjacent motion without using learned recognition. Sampling alone cannot know string
topology, so direct agent inspection and `variation_tags` complete the coverage
process.

## Deterministic selection

`sample_video_frames.py` performs four steps:

1. Hash each source video and preserve it as one stable source group.
2. Generate candidates across nearly the full duration of every video.
3. Select one anchor from each temporal stratum, preferring distance from prior
   anchors in low-resolution color, intensity, and edge appearance.
4. Extract configured neighbor offsets around every anchor for continuity work.

The descriptor cannot identify a yoyo, hand, string, or pose. The manifest
records `recognition_model_used=false`, parameters, source hashes, timestamps,
and anchor/context roles. This manifest is required by annotation project
initialization and remains the authority for video provenance.

## Agent coverage pass

Inspect the anchor contact sheet and raw frames. Retain reviewed positives and
hard negatives and seek multiple tags such as loop, crossing, occluded, blur,
low contrast, edge clipping, and background-edge distractors.

Use neighbor frames to improve trajectory consistency, but count the dispersed
anchor as the scene-diversity unit. Many consecutive frames of one formation do
not replace source or topology diversity.

Inspect a short temporal window around every trick anchor to distinguish a
horizontal launch from a normal throw. Do not ask the appearance sampler to make
this semantic decision and do not classify from a static horizontal rope span.

Do not create evaluation partitions in this skill. Pass source groups, variation
tags, visibility states, and review metadata to the downstream partitioner so it
can build leakage-free train/validation/test collections later.
