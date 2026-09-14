"""Walk a drive, identify footage, and read each clip's technical metadata."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterator

from .config import UNSUPPORTED_EXTENSIONS, Config
from .util import ffprobe_json, parse_fraction

log = logging.getLogger("stillharvest")

# pix_fmt substrings -> bits per component
_DEPTH_HINTS = (("16", 16), ("14", 14), ("12", 12), ("10", 10))


def iter_media_files(root: str | Path, cfg: Config) -> Iterator[Path]:
    """Yield every candidate video file below ``root``, skipping system cruft."""
    root = Path(root)
    excluded = {name.lower() for name in cfg.exclude_dirs}
    wanted = tuple(ext.lower() for ext in cfg.extensions)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune in place so os.walk never descends into them.
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in excluded and not d.startswith(".")
        ]
        for name in sorted(filenames):
            if name.startswith("."):          # AppleDouble ._ sidecars etc.
                continue
            if name.lower().endswith(wanted):
                yield Path(dirpath) / name


def classify_unsupported(root: str | Path, cfg: Config) -> list[Path]:
    """Camera-raw files FFmpeg cannot open. Reported, never silently dropped."""
    root = Path(root)
    excluded = {name.lower() for name in cfg.exclude_dirs}
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d for d in dirnames if d.lower() not in excluded and not d.startswith(".")
        ]
        for name in filenames:
            if name.lower().endswith(UNSUPPORTED_EXTENSIONS):
                found.append(Path(dirpath) / name)
    return found


def _bit_depth(pix_fmt: str) -> int:
    for token, depth in _DEPTH_HINTS:
        if token in pix_fmt:
            return depth
    return 8


def _rotation(stream: dict[str, Any]) -> int:
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            try:
                return int(round(float(side["rotation"]))) % 360
            except (TypeError, ValueError):
                pass
    tag = (stream.get("tags") or {}).get("rotate")
    if tag:
        try:
            return int(round(float(tag))) % 360
        except (TypeError, ValueError):
            pass
    return 0


def _first_tag(probe: dict[str, Any], stream: dict[str, Any], *keys: str) -> str | None:
    sources = [stream.get("tags") or {}, (probe.get("format") or {}).get("tags") or {}]
    for tags in sources:
        lowered = {str(k).lower(): v for k, v in tags.items()}
        for key in keys:
            value = lowered.get(key.lower())
            if value:
                return str(value)
    return None


def shoot_and_reel(path: Path, root: Path) -> tuple[str, str]:
    """Group footage the way a shoot is actually laid out on the card/drive.

    ``shoot`` is the top folder under the scan root (the job); ``reel`` is the
    immediate parent folder (usually the camera card, e.g. A001).
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        return root.name or "footage", path.parent.name or "reel"
    parts = relative.parts
    shoot = parts[0] if len(parts) > 1 else (root.name or "footage")
    reel = path.parent.name if path.parent != root else shoot
    return shoot, reel


def probe_clip(path: Path, root: Path, cfg: Config) -> dict[str, Any]:
    """Build the ``clips`` row for one file. ``status`` says whether it is usable."""
    stat = path.stat()
    shoot, reel = shoot_and_reel(path, root)
    row: dict[str, Any] = {
        "path": str(path),
        "rel_path": str(path.relative_to(root)) if _under(path, root) else path.name,
        "shoot": shoot,
        "reel": reel,
        "size_bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "duration": 0.0, "fps": 0.0, "width": 0, "height": 0, "rotation": 0,
        "codec": None, "pix_fmt": None, "bit_depth": 8,
        "captured_at": None, "camera": None,
        "probe_json": None, "status": "new", "note": None,
    }

    if stat.st_size < cfg.min_file_bytes:
        row["status"] = "skipped"
        row["note"] = "below min-file-size"
        return row

    probe = ffprobe_json(str(path))
    if not probe:
        row["status"] = "error"
        row["note"] = "unreadable by ffprobe"
        return row

    streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    # Skip cover art / thumbnail streams masquerading as video.
    streams = [s for s in streams if (s.get("disposition") or {}).get("attached_pic", 0) != 1]
    if not streams:
        row["status"] = "skipped"
        row["note"] = "no video stream"
        return row

    stream = streams[0]
    fmt = probe.get("format") or {}
    duration = parse_fraction(stream.get("duration")) or parse_fraction(fmt.get("duration"))
    fps = parse_fraction(stream.get("avg_frame_rate")) or parse_fraction(stream.get("r_frame_rate"), 25.0)
    width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
    rotation = _rotation(stream)

    make = _first_tag(probe, stream, "com.apple.quicktime.make", "make", "manufacturer")
    model = _first_tag(probe, stream, "com.apple.quicktime.model", "model", "encoder")

    row.update({
        "duration": round(duration, 3),
        "fps": round(fps, 6),
        "width": width,
        "height": height,
        "rotation": rotation,
        "codec": stream.get("codec_name"),
        "pix_fmt": stream.get("pix_fmt"),
        "bit_depth": _bit_depth(str(stream.get("pix_fmt") or "")),
        "captured_at": _first_tag(
            probe, stream,
            "com.apple.quicktime.creationdate", "creation_time", "date", "date_recorded",
        ),
        "camera": " ".join(x for x in (make, model) if x) or None,
        "probe_json": None,
    })

    if duration < cfg.min_duration:
        row["status"] = "skipped"
        row["note"] = f"duration {duration:.2f}s below minimum"
    elif width < 320 or height < 240:
        row["status"] = "skipped"
        row["note"] = f"resolution {width}x{height} too small"
    return row


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def display_size(width: int, height: int, rotation: int) -> tuple[int, int]:
    """Frame size after FFmpeg applies the display matrix."""
    return (height, width) if rotation % 180 == 90 else (width, height)
