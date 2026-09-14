"""The analysis pass: decode each clip once, cheaply, and measure every sampled frame.

Footage is decoded at a small analysis resolution (512px by default) at a few
frames per second. That single pass yields shot boundaries, per-frame quality
measurements, and a perceptual hash - enough to decide which moments deserve a
full-resolution extraction later.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from .config import Config
from .metrics import apply_faces, detect_faces, faces_available, measure
from .probe import display_size

log = logging.getLogger("stillharvest")


# --------------------------------------------------------------------------
# decoding
# --------------------------------------------------------------------------

def analysis_dimensions(width: int, height: int, rotation: int, target_long_edge: int) -> tuple[int, int]:
    """Even-numbered analysis size preserving the clip's display aspect ratio.

    The *long* edge is capped, so a vertical clip costs the same to analyse as a
    horizontal one instead of ballooning to a 512x910 frame.
    """
    dw, dh = display_size(width, height, rotation)
    if dw <= 0 or dh <= 0:
        return 0, 0
    scale = min(1.0, target_long_edge / float(max(dw, dh)))
    aw = max(64, int(round(dw * scale)) & ~1)
    ah = max(64, int(round(dh * scale)) & ~1)
    return aw, ah


def iter_frames(
    path: str,
    out_w: int,
    out_h: int,
    *,
    fps: float,
    start: float = 0.0,
    duration: float | None = None,
    threads: int = 1,
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield (timestamp, RGB array) pairs decoded by FFmpeg.

    Timestamps are ``start + index / fps``; exact to within one sample interval,
    which the refine step in :mod:`stillharvest.extract` then tightens.
    """
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-threads", str(max(1, threads))]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", path]
    if duration is not None and duration > 0:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += [
        "-map", "0:v:0",
        "-an", "-sn", "-dn",
        "-vf", f"fps={fps:g},scale={out_w}:{out_h}:flags=area",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
    ]

    frame_bytes = out_w * out_h * 3
    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=frame_bytes * 2,
    )
    assert proc.stdout is not None
    index = 0
    try:
        buffer = bytearray(frame_bytes)
        view = memoryview(buffer)
        while True:
            filled = 0
            while filled < frame_bytes:
                got = proc.stdout.readinto(view[filled:])
                if not got:
                    break
                filled += got
            if filled < frame_bytes:
                break
            frame = np.frombuffer(bytes(buffer), dtype=np.uint8).reshape(out_h, out_w, 3)
            yield start + index / fps, frame
            index += 1
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        stderr = b""
        try:
            stderr = proc.stderr.read() if proc.stderr else b""
            proc.stderr.close()
        except Exception:
            pass
        if proc.returncode not in (0, None) and stderr:
            log.debug("ffmpeg (%s): %s", Path(path).name, stderr.decode("utf-8", "replace")[:400])


# --------------------------------------------------------------------------
# shot segmentation
# --------------------------------------------------------------------------

def _histogram(gray: np.ndarray, bins: int = 48, full: np.ndarray | None = None) -> np.ndarray:
    """Normalised luma histogram for shot detection.

    Reuses the 256-bin histogram already computed for exposure when available,
    rebinning it instead of walking the pixels a second time.
    """
    if full is not None and 256 % bins == 0:
        coarse = full.reshape(bins, 256 // bins).sum(axis=1)
    else:
        coarse, _ = np.histogram(gray, bins=bins, range=(0.0, 255.0))
    coarse = coarse.astype(np.float32)
    total = coarse.sum()
    return coarse / (total if total else 1.0)


def scene_distance(gray: np.ndarray, prev_gray: np.ndarray,
                   hist: np.ndarray, prev_hist: np.ndarray) -> float:
    """0 (identical) .. 1 (unrelated). Blends tonal and spatial change."""
    hist_dist = 0.5 * float(np.abs(hist - prev_hist).sum())
    pixel_dist = float(np.mean(np.abs(gray - prev_gray))) / 255.0
    return 0.6 * hist_dist + 0.4 * min(1.0, pixel_dist * 4.0)


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def _soft(value: float, half: float) -> float:
    """Saturating 0..1 curve; returns 0.5 at ``half``."""
    value = max(0.0, value)
    return value / (value + half) if (value + half) > 0 else 0.0


def sharpness_score(m: dict[str, Any]) -> float:
    return 0.6 * _soft(m["lap_var"], 300.0) + 0.4 * _soft(m["tenengrad"], 300.0)


def exposure_score(m: dict[str, Any]) -> float:
    # Distance from a comfortable mid-tone, then penalties for lost detail.
    balance = max(0.0, 1.0 - abs(m["mean"] - 112.0) / 112.0)
    dynamic_range = min(1.0, (m["p95"] - m["p05"]) / 170.0)
    score = 0.55 * balance + 0.45 * dynamic_range
    score *= max(0.0, 1.0 - m["clipped_high"] * 3.0)
    score *= max(0.0, 1.0 - max(0.0, m["crushed_low"] - 0.15) * 1.6)
    return max(0.0, min(1.0, score))


def face_score(m: dict[str, Any], detection_on: bool) -> float:
    if not detection_on:
        return 0.5                      # neutral: the weight cannot bias anything
    if not m["face_count"]:
        return 0.3                      # landscapes stay viable, just not favoured
    frac = m["face_height_frac"]
    # Faces that fill 12-55% of frame height read best as portraits.
    if frac <= 0.0:
        size = 0.0
    elif frac < 0.12:
        size = frac / 0.12
    elif frac <= 0.55:
        size = 1.0
    else:
        size = max(0.0, 1.0 - (frac - 0.55) / 0.45)
    crowd = min(1.0, 0.75 + 0.25 * min(m["face_count"], 4) / 4.0)
    return max(0.0, min(1.0, 0.55 + 0.45 * size * crowd))


def composite_score(m: dict[str, Any], cfg: Config, detection_on: bool) -> float:
    w = cfg.weights.normalised()
    parts = {
        "sharpness": sharpness_score(m),
        "exposure": exposure_score(m),
        "contrast": min(1.0, m["std"] / 70.0),
        "composition": m["composition"],
        "faces": face_score(m, detection_on),
        "colorfulness": _soft(m["colorfulness"], 30.0),
        "stability": max(0.0, 1.0 - m["motion"] / max(cfg.max_motion, 1e-6)),
    }
    return round(100.0 * sum(w[k] * v for k, v in parts.items()), 2)


def rejection_reason(m: dict[str, Any], cfg: Config) -> str | None:
    """Hard gates - a frame failing any of these can never be a usable photo."""
    if m["mean"] < cfg.min_luma:
        return "too dark"
    if m["mean"] > cfg.max_luma:
        return "blown out"
    if m["std"] < cfg.min_contrast:
        return "flat/blank frame"
    if m["lap_var"] < cfg.min_sharpness:
        return "out of focus"
    if m["motion"] > cfg.max_motion:
        return "motion smear / transition"
    if m["clipped_high"] > cfg.max_clipped_highlight:
        return "clipped highlights"
    if m["crushed_low"] > cfg.max_crushed_shadow:
        return "crushed shadows"
    return None


# --------------------------------------------------------------------------
# per-clip driver
# --------------------------------------------------------------------------

def analyze_clip(clip: dict[str, Any], cfg: Config, *, threads: int = 1) -> dict[str, Any]:
    """Measure one clip. Returns {'frames': [...], 'shots': int, 'note': str|None}."""
    out_w, out_h = analysis_dimensions(
        int(clip["width"]), int(clip["height"]), int(clip.get("rotation") or 0),
        cfg.analysis_width,
    )
    if out_w == 0:
        return {"frames": [], "shots": 0, "note": "unknown frame size"}

    duration = float(clip["duration"])
    start = min(cfg.skip_head, max(0.0, duration * 0.02))
    span = max(0.0, duration - start - min(cfg.skip_tail, duration * 0.02))
    if span <= 0:
        return {"frames": [], "shots": 0, "note": "clip too short to sample"}

    detection_on = faces_available()
    rows: list[dict[str, Any]] = []
    prev_gray: np.ndarray | None = None
    prev_hist: np.ndarray | None = None
    shot = 0
    shot_started = start

    for timestamp, frame in iter_frames(
        clip["path"], out_w, out_h,
        fps=cfg.sample_fps, start=start, duration=span, threads=threads,
    ):
        # Faces are measured later, and only for frames that survive the hard
        # gates - detection costs more than every other metric combined, and
        # most rejected frames are dark, blurred or mid-transition anyway.
        m = measure(frame, prev_gray, want_faces=False)
        gray = m.pop("_gray")
        hist = _histogram(gray, full=m.pop("_hist"))

        if prev_gray is not None and prev_hist is not None:
            distance = scene_distance(gray, prev_gray, hist, prev_hist)
            if distance > cfg.scene_threshold and (timestamp - shot_started) >= cfg.min_shot_seconds:
                shot += 1
                shot_started = timestamp
                m["motion"] = 0.0      # a cut is not camera movement; don't penalise it
        else:
            m["motion"] = 0.0          # first frame has nothing to compare against

        reason = rejection_reason(m, cfg)
        if reason is None and detection_on:
            apply_faces(m, frame, gray.shape, detect_faces(frame))

        rows.append({
            "t": round(timestamp, 3),
            "shot": shot,
            "score": composite_score(m, cfg, detection_on),
            "phash": m["phash"],
            "rejected": reason,
            "metrics": {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in m.items() if k != "phash"
            },
        })
        prev_gray, prev_hist = gray, hist

    return {"frames": rows, "shots": shot + 1 if rows else 0, "note": None}
