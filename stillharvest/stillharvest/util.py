"""Process helpers, ffmpeg/ffprobe wrappers, and small formatting utilities."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Sequence

log = logging.getLogger("stillharvest")


class ToolMissing(RuntimeError):
    pass


def require_tools(*names: str) -> None:
    missing = [n for n in names if shutil.which(n) is None]
    if missing:
        raise ToolMissing(
            "Missing required executable(s): %s. Install FFmpeg "
            "(macOS: `brew install ffmpeg`, Windows: `winget install Gyan.FFmpeg`, "
            "Debian/Ubuntu: `sudo apt install ffmpeg`)." % ", ".join(missing)
        )


def run(cmd: Sequence[str], *, capture: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run a command, never inheriting stdin (ffmpeg steals it otherwise)."""
    return subprocess.run(
        list(cmd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        timeout=timeout,
    )


def ffprobe_json(path: str, *, timeout: float = 120.0) -> dict[str, Any]:
    """Return the full ffprobe description of a media file, or {} if unreadable."""
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", "-show_entries", "stream_side_data",
        path,
    ]
    try:
        proc = run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        log.warning("ffprobe timed out: %s", path)
        return {}
    if proc.returncode != 0:
        log.warning("ffprobe failed (%s): %s", proc.returncode, path)
        return {}
    try:
        return json.loads(proc.stdout or b"{}")
    except json.JSONDecodeError:
        return {}


def parse_fraction(value: Any, default: float = 0.0) -> float:
    """Parse ffprobe rationals like '24000/1001'."""
    if value in (None, "", "0/0", "N/A"):
        return default
    try:
        text = str(value)
        if "/" in text:
            num, den = text.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else default
        return float(text)
    except (ValueError, ZeroDivisionError):
        return default


def timecode(seconds: float, fps: float) -> str:
    """HH-MM-SS-FF, filename safe."""
    fps = fps if fps and fps > 0 else 25.0
    if seconds < 0:
        seconds = 0.0
    total_frames = int(round(seconds * fps))
    frames = total_frames % int(round(fps))
    total_secs = total_frames // int(round(fps))
    return "%02d-%02d-%02d-%02d" % (
        total_secs // 3600, (total_secs // 60) % 60, total_secs % 60, frames,
    )


def human_duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, m, s = seconds // 3600, (seconds // 60) % 60, seconds % 60
    return f"{h:d}h{m:02d}m{s:02d}s" if h else f"{m:d}m{s:02d}s"


def human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}PB"


def slugify(text: str, *, maxlen: int = 48) -> str:
    keep = []
    for ch in text.strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_.":
            keep.append("-")
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-._")[:maxlen] or "untitled"


_SIZE_UNITS = {"b": 1, "k": 1024, "kb": 1024, "m": 1024**2, "mb": 1024**2,
               "g": 1024**3, "gb": 1024**3}


def parse_size(text: str) -> int:
    """Accept '800k', '1.5MB', '2000000' and return bytes."""
    raw = str(text).strip().lower().replace(" ", "")
    if not raw:
        raise ValueError("empty size")
    for suffix in sorted(_SIZE_UNITS, key=len, reverse=True):
        if raw.endswith(suffix) and raw[: -len(suffix)]:
            return int(float(raw[: -len(suffix)]) * _SIZE_UNITS[suffix])
    return int(float(raw))
