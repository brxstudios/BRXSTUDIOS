"""Export the chosen moments as full-resolution stills.

The analysis pass works on a 512px proxy sampled a few times a second, so its
timestamps are only accurate to within one sample interval. Before exporting,
``refine_timestamp`` re-decodes a short window around each pick at the clip's
native frame rate and moves to the genuinely sharpest frame - which is the
difference between a keeper and a slightly smeared near-miss.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any


from .analyze import analysis_dimensions, iter_frames
from .config import Config
from .metrics import laplacian_variance, luma
from .probe import display_size
from .util import slugify, timecode

log = logging.getLogger("stillharvest")

_EXT_FOR_FORMAT = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "tiff": ".tif"}


def escape_filter_path(path: str | Path) -> str:
    """Escape a filesystem path for use inside an FFmpeg filtergraph argument.

    Windows drive letters and any ``:``/``'``/``\\`` in the path would otherwise
    be read as filter syntax.
    """
    text = str(path).replace("\\", "/")
    for char in ("\\", "'", ":", "[", "]", ",", ";"):
        text = text.replace(char, "\\" + char)
    return text


def refine_timestamp(clip: dict[str, Any], t: float, cfg: Config) -> float:
    """Search +/- ``refine_window`` seconds at native frame rate for peak sharpness."""
    if not cfg.refine:
        return t
    fps = float(clip.get("fps") or 25.0)
    if fps <= 0:
        return t
    duration = float(clip.get("duration") or 0.0)
    start = max(0.0, t - cfg.refine_window)
    span = min(cfg.refine_window * 2.0, max(0.0, duration - start))
    if span <= 1.0 / fps:
        return t

    out_w, out_h = analysis_dimensions(
        int(clip["width"]), int(clip["height"]), int(clip.get("rotation") or 0), 384
    )
    if out_w == 0:
        return t

    best_t, best_sharp = t, -1.0
    try:
        for timestamp, frame in iter_frames(
            clip["path"], out_w, out_h, fps=fps, start=start, duration=span
        ):
            sharpness = laplacian_variance(luma(frame))
            if sharpness > best_sharp:
                best_sharp, best_t = sharpness, timestamp
    except Exception as exc:
        log.debug("refine failed for %s @%.2f: %s", clip["path"], t, exc)
        return t
    return round(best_t, 4)


def _output_args(cfg: Config) -> tuple[list[str], str]:
    fmt = cfg.still_format.lower()
    if fmt in ("jpg", "jpeg"):
        return ["-q:v", str(max(1, min(31, cfg.jpeg_quality)))], ".jpg"
    if fmt == "png":
        pix = "rgb48be" if cfg.png_bit_depth >= 16 else "rgb24"
        return ["-pix_fmt", pix, "-compression_level", "6"], ".png"
    if fmt in ("tif", "tiff"):
        return ["-pix_fmt", "rgb24"], ".tif"
    return ["-q:v", "2"], ".jpg"


def build_chain(cfg: Config) -> str:
    """Filter steps applied to the exported still, in order."""
    steps = []
    if cfg.lut:
        steps.append(f"lut3d=file={escape_filter_path(cfg.lut)}:interp=tetrahedral")
    if cfg.max_still_width and cfg.max_still_width > 0:
        steps.append(f"scale='min({cfg.max_still_width},iw)':-2:flags=lanczos")
    return ",".join(steps)


def validate_lut(lut: str | Path) -> None:
    """Fail fast on a missing or unreadable .cube, rather than per extracted frame."""
    path = Path(lut)
    if not path.is_file():
        raise FileNotFoundError(f"LUT not found: {path}")
    probe = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi",
         "-i", "color=c=gray:s=64x64:d=1",
         "-vf", f"lut3d=file={escape_filter_path(path)}",
         "-frames:v", "1", "-f", "null", "-"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if probe.returncode != 0:
        detail = probe.stderr.decode("utf-8", "replace").strip()[:300]
        raise ValueError(f"FFmpeg cannot apply LUT {path}: {detail}")


def still_filename(clip: dict[str, Any], t: float, score: float, ext: str) -> str:
    stem = Path(clip["path"]).stem
    tc = timecode(t, float(clip.get("fps") or 25.0))
    parts = [
        slugify(str(clip.get("shoot") or "footage"), maxlen=24),
        slugify(str(clip.get("reel") or ""), maxlen=16),
        slugify(stem, maxlen=32),
        tc,
        f"s{int(round(score)):03d}",
    ]
    return "_".join(p for p in parts if p) + ext


def extract_still(
    clip: dict[str, Any], t: float, dest: Path, thumb: Path | None, cfg: Config
) -> bool:
    """Write one full-resolution still (and optionally its thumbnail)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    chain = build_chain(cfg)
    codec_args, _ = _output_args(cfg)

    head = f"[0:v]{chain}," if chain else "[0:v]"
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", clip["path"]]

    if thumb is not None:
        thumb.parent.mkdir(parents=True, exist_ok=True)
        graph = (
            f"{head}split=2[full][tmp];"
            f"[tmp]scale='min({cfg.thumb_width},iw)':-2:flags=area[thumb]"
        )
        cmd += [
            "-filter_complex", graph,
            "-map", "[full]", "-frames:v", "1", *codec_args, str(dest),
            "-map", "[thumb]", "-frames:v", "1", "-q:v", "4", str(thumb),
        ]
    else:
        if chain:
            cmd += ["-vf", chain]
        cmd += ["-map", "0:v:0", "-frames:v", "1", *codec_args, str(dest)]

    proc = subprocess.run(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
        log.warning(
            "extract failed %s @%.3f: %s",
            Path(clip["path"]).name, t,
            proc.stderr.decode("utf-8", "replace").strip()[:300],
        )
        dest.unlink(missing_ok=True)
        return False
    return True


def still_dimensions(clip: dict[str, Any], cfg: Config) -> tuple[int, int]:
    """Expected output size, accounting for rotation and any width cap."""
    w, h = display_size(
        int(clip["width"]), int(clip["height"]), int(clip.get("rotation") or 0)
    )
    cap = cfg.max_still_width
    if cap and cap > 0 and w > cap:
        h = int(round(h * cap / w)) & ~1
        w = cap
    return w, h


def extension_for(cfg: Config) -> str:
    return _EXT_FOR_FORMAT.get(cfg.still_format.lower(), ".jpg")
