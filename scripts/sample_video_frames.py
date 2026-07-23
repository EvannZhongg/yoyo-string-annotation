#!/usr/bin/env python3
"""Sample source-balanced, temporally dispersed video frames without recognition models."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
SCHEMA_VERSION = "agent_video_sampling_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def clean_id(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "_.-" else "-" for character in value)
    return cleaned.strip("-.") or "video"


def parse_offsets(value: str) -> list[int]:
    if not value.strip():
        return []
    try:
        return sorted({int(item.strip()) for item in value.split(",") if int(item.strip()) != 0})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("neighbor offsets must be comma-separated frame offsets") from exc


def descriptor(frame: np.ndarray) -> np.ndarray:
    """Return a cheap appearance descriptor; it performs no object recognition."""
    small = cv2.resize(frame, (48, 27), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    histograms = [
        cv2.calcHist([hsv], [channel], None, [bins], bounds).reshape(-1)
        for channel, bins, bounds in ((0, 12, [0, 180]), (1, 8, [0, 256]), (2, 8, [0, 256]))
    ]
    appearance = cv2.resize(gray, (16, 9), interpolation=cv2.INTER_AREA).reshape(-1).astype(np.float32)
    edges = cv2.Canny(gray, 60, 160)
    features = np.concatenate([*(item.astype(np.float32) for item in histograms), appearance, [float(edges.mean())]])
    norm = float(np.linalg.norm(features))
    return features / norm if norm else features


def appearance_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(1.0 - np.clip(np.dot(left, right), -1.0, 1.0))


@dataclass
class Candidate:
    frame_index: int
    frame: np.ndarray
    descriptor: np.ndarray


def read_candidates(capture: cv2.VideoCapture, indices: list[int]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if ok and frame is not None:
            candidates.append(Candidate(frame_index, frame, descriptor(frame)))
    return candidates


def select_anchors(candidates: list[Candidate], frame_count: int, count: int) -> list[Candidate]:
    """Choose one frame per temporal stratum, preferring appearance diversity."""
    if not candidates or count <= 0:
        return []
    count = min(count, len(candidates))
    selected: list[Candidate] = []
    for stratum in range(count):
        start = frame_count * stratum / count
        stop = frame_count * (stratum + 1) / count
        pool = [item for item in candidates if start <= item.frame_index < stop and item not in selected]
        if not pool:
            pool = [item for item in candidates if item not in selected]
        center = (start + stop) / 2.0

        def score(item: Candidate) -> tuple[float, float, int]:
            diversity = min((appearance_distance(item.descriptor, prior.descriptor) for prior in selected), default=0.0)
            temporal_centering = 1.0 - abs(item.frame_index - center) / max(1.0, stop - start)
            return diversity, temporal_centering, -item.frame_index

        selected.append(max(pool, key=score))
    return sorted(selected, key=lambda item: item.frame_index)


def candidate_indices(frame_count: int, count: int, oversample: int, edge_fraction: float) -> list[int]:
    if frame_count <= 0:
        return []
    start = min(frame_count - 1, max(0, round(frame_count * edge_fraction)))
    stop = min(frame_count - 1, max(start, round((frame_count - 1) * (1.0 - edge_fraction))))
    sample_count = min(max(count, count * oversample), stop - start + 1)
    return sorted({int(round(value)) for value in np.linspace(start, stop, sample_count)})


def extract_frame(capture: cv2.VideoCapture, frame_index: int) -> np.ndarray | None:
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    return frame if ok else None


def save_contact_sheet(records: list[dict[str, Any]], output: Path) -> None:
    anchors = [record for record in records if record["role"] == "anchor"]
    if not anchors:
        return
    cell_width, cell_height = 360, 235
    columns = min(4, len(anchors))
    rows = math.ceil(len(anchors) / columns)
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#16181b")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, record in enumerate(anchors):
        with Image.open(record["output_image"]) as opened:
            image = opened.convert("RGB")
        image.thumbnail((cell_width, cell_height - 35), Image.Resampling.LANCZOS)
        x = index % columns * cell_width
        y = index // columns * cell_height
        sheet.paste(image, (x + (cell_width - image.width) // 2, y + 30))
        timestamp = record.get("timestamp_s")
        time_text = f"{timestamp:.2f}s" if isinstance(timestamp, (int, float)) else "unknown"
        caption = f"{record['source_group']} f={record['frame_index']} t={time_text}"
        draw.rectangle((x, y, x + cell_width, y + 29), fill="#25292e")
        draw.text((x + 7, y + 9), caption[:55], fill="white", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def process_video(path: Path, output: Path, args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_sha256 = sha256_file(path)
    source_group = f"{clean_id(path.stem)[:40]}-{source_sha256[:10]}"
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    indices = candidate_indices(frame_count, args.frames_per_video, args.oversample_factor, args.edge_fraction)
    candidates = read_candidates(capture, indices)
    anchors = select_anchors(candidates, frame_count, args.frames_per_video)
    records: list[dict[str, Any]] = []
    written: set[int] = set()
    anchor_indices = {item.frame_index for item in anchors}
    for sequence_number, anchor in enumerate(anchors, start=1):
        sequence_id = f"seq-{sequence_number:03d}-anchor-{anchor.frame_index:08d}"
        for frame_index in [anchor.frame_index, *(anchor.frame_index + offset for offset in args.neighbor_offsets)]:
            is_anchor = frame_index == anchor.frame_index
            if frame_index < 0 or frame_index >= frame_count or frame_index in written:
                continue
            if not is_anchor and frame_index in anchor_indices:
                continue
            frame = anchor.frame if frame_index == anchor.frame_index else extract_frame(capture, frame_index)
            if frame is None:
                continue
            role = "anchor" if is_anchor else "temporal_context"
            filename = f"{sequence_id}_{role}_frame_{frame_index:08d}.jpg"
            image_path = output / "images" / source_group / filename
            image_path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality]):
                raise OSError(f"could not write image: {image_path}")
            written.add(frame_index)
            records.append(
                {
                    "source_video": str(path),
                    "source_video_sha256": source_sha256,
                    "source_group": source_group,
                    "sequence_id": sequence_id,
                    "role": role,
                    "anchor_frame_index": anchor.frame_index,
                    "frame_index": frame_index,
                    "timestamp_s": round(frame_index / fps, 6) if fps else None,
                    "image_size": [width, height],
                    "output_image": str(image_path.resolve()),
                    "output_image_sha256": sha256_file(image_path),
                }
            )
    capture.release()
    source = {
        "source_video": str(path),
        "source_video_sha256": source_sha256,
        "source_group": source_group,
        "fps": fps,
        "frame_count": frame_count,
        "image_size": [width, height],
        "candidate_count": len(candidates),
        "anchor_count": len(anchors),
        "written_count": len(records),
    }
    return source, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos", required=True, help="One video or a directory searched recursively.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames-per-video", type=int, default=12, help="Number of temporally stratified anchor frames.")
    parser.add_argument("--oversample-factor", type=int, default=5, help="Candidates per selected anchor before diversity selection.")
    parser.add_argument("--neighbor-offsets", type=parse_offsets, default=parse_offsets("-2,-1,1,2"))
    parser.add_argument("--edge-fraction", type=float, default=0.04)
    parser.add_argument("--jpeg-quality", type=int, default=96)
    args = parser.parse_args()
    if args.frames_per_video < 1 or args.oversample_factor < 1:
        parser.error("frames-per-video and oversample-factor must be positive")
    if not 0 <= args.edge_fraction < 0.5:
        parser.error("edge-fraction must be in [0, 0.5)")

    videos_root = Path(args.videos).resolve()
    output = Path(args.output).resolve()
    manifest_path = output / "sampling_manifest.json"
    if manifest_path.exists():
        parser.error(f"output already contains a sampling manifest: {manifest_path}")
    videos = [videos_root] if videos_root.is_file() else sorted(
        path for path in videos_root.rglob("*") if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        parser.error(f"no supported videos found under {videos_root}")

    sources: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in videos:
        try:
            source, source_records = process_video(path, output, args)
        except Exception as exc:
            failures.append({"source_video": str(path), "error": str(exc)})
            continue
        sources.append(source)
        records.extend(source_records)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "sampling_method": "source-balanced temporal strata plus non-semantic appearance diversity",
        "recognition_model_used": False,
        "videos_root": str(videos_root),
        "output": str(output),
        "parameters": {
            "frames_per_video": args.frames_per_video,
            "oversample_factor": args.oversample_factor,
            "neighbor_offsets": args.neighbor_offsets,
            "edge_fraction": args.edge_fraction,
        },
        "source_count": len(sources),
        "record_count": len(records),
        "failure_count": len(failures),
        "sources": sources,
        "records": records,
        "failures": failures,
    }
    write_json(manifest_path, manifest)
    save_contact_sheet(records, output / "anchor_contact_sheet.jpg")
    print(json.dumps({key: manifest[key] for key in ("source_count", "record_count", "failure_count", "output")}, ensure_ascii=False, indent=2))
    return 1 if not sources else 0


if __name__ == "__main__":
    raise SystemExit(main())
