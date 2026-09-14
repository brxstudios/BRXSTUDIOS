"""Per-frame image measurements.

Everything here operates on small RGB arrays (uint8, H x W x 3) pulled from the
analysis decode pass, so the whole drive can be measured without touching
full-resolution pixels. NumPy is the only hard dependency; OpenCV, when present,
adds face detection.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from . import faces as _faces


def faces_available() -> bool:
    """True when a face-detection backend is loaded (see :mod:`stillharvest.faces`)."""
    return _faces.available()


# --- basic conversions ----------------------------------------------------

def luma(rgb: np.ndarray) -> np.ndarray:
    """Rec.601 luma as float32, matching what the eye weights."""
    f = rgb.astype(np.float32)
    return 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]


# --- focus ----------------------------------------------------------------

def laplacian_variance(gray: np.ndarray) -> float:
    """Classic focus measure: variance of a 4-neighbour Laplacian."""
    lap = (
        -4.0 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1] + gray[2:, 1:-1]
        + gray[1:-1, :-2] + gray[1:-1, 2:]
    )
    return float(lap.var())


def tenengrad(gray: np.ndarray) -> float:
    """Mean Sobel gradient energy - steadier than Laplacian on noisy footage."""
    gx = gray[1:-1, 2:] - gray[1:-1, :-2]
    gy = gray[2:, 1:-1] - gray[:-2, 1:-1]
    return float(np.mean(gx * gx + gy * gy))


def edge_density(gray: np.ndarray, threshold: float = 18.0) -> float:
    gx = np.abs(gray[1:-1, 2:] - gray[1:-1, :-2])
    gy = np.abs(gray[2:, 1:-1] - gray[:-2, 1:-1])
    return float(np.mean((gx + gy) > threshold))


# --- tone -----------------------------------------------------------------

def gray_histogram(gray: np.ndarray) -> np.ndarray:
    """256-bin luma histogram. One pass of bincount, reused by several metrics."""
    return np.bincount(gray.astype(np.uint8).ravel(), minlength=256).astype(np.float64)


def exposure_stats(gray: np.ndarray, hist: np.ndarray | None = None) -> dict[str, float]:
    """Tone statistics derived from the histogram.

    Everything here is computed from 256 bins rather than the pixels, which
    makes it ~10x cheaper than calling ``np.percentile`` on a full frame - and
    this runs on every sampled frame of every clip on the drive.
    """
    if hist is None:
        hist = gray_histogram(gray)
    total = float(hist.sum()) or 1.0
    levels = np.arange(256, dtype=np.float64)

    mean = float((hist * levels).sum() / total)
    variance = float((hist * levels * levels).sum() / total) - mean * mean
    cumulative = np.cumsum(hist)

    def percentile(fraction: float) -> float:
        return float(np.searchsorted(cumulative, fraction * total))

    return {
        "mean": mean,
        "std": float(np.sqrt(max(0.0, variance))),
        "clipped_high": float(hist[252:].sum() / total),
        "crushed_low": float(hist[:7].sum() / total),
        "p05": percentile(0.05),
        "p95": percentile(0.95),
    }


def colorfulness(rgb: np.ndarray) -> float:
    """Hasler & Susstrunk colourfulness; near zero for monochrome frames."""
    f = rgb.astype(np.float32)
    rg = f[:, :, 0] - f[:, :, 1]
    yb = 0.5 * (f[:, :, 0] + f[:, :, 1]) - f[:, :, 2]
    return float(
        math.sqrt(rg.std() ** 2 + yb.std() ** 2)
        + 0.3 * math.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )


def colour_temperature(rgb: np.ndarray) -> str:
    f = rgb.reshape(-1, 3).astype(np.float32).mean(axis=0)
    r, g, b = float(f[0]), float(f[1]), float(f[2])
    spread = max(r, g, b) - min(r, g, b)
    if spread < 6.0:
        return "neutral"
    return "warm" if r > b else "cool"


# --- composition ----------------------------------------------------------

def thirds_score(gray: np.ndarray) -> tuple[float, float, float]:
    """Where the visual weight sits, scored against the rule-of-thirds points.

    Returns (score 0..1, centroid_x 0..1, centroid_y 0..1).
    """
    gx = np.abs(gray[1:-1, 2:] - gray[1:-1, :-2])
    gy = np.abs(gray[2:, 1:-1] - gray[:-2, 1:-1])
    energy = gx + gy
    total = float(energy.sum())
    if total <= 1e-6:
        return 0.0, 0.5, 0.5
    h, w = energy.shape
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    cy = float((energy * ys).sum() / total) / max(h - 1, 1)
    cx = float((energy * xs).sum() / total) / max(w - 1, 1)
    best = min(
        math.hypot(cx - px, cy - py)
        for px in (1 / 3, 2 / 3) for py in (1 / 3, 2 / 3)
    )
    # 0.236 is the distance from a thirds point to the frame centre.
    return float(max(0.0, 1.0 - best / 0.47)), cx, cy


# --- identity -------------------------------------------------------------

def dhash(gray: np.ndarray, size: int = 8) -> int:
    """64-bit difference hash used to collapse near-identical frames."""
    small = _resize_nearest(gray, size + 1, size)
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for value in diff.flatten():
        bits = (bits << 1) | int(value)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def phash_to_hex(value: int | None) -> str | None:
    """dHash is a full 64-bit *unsigned* value; SQLite integers are signed, so
    the top-bit-set half of the range overflows. Store it as fixed-width hex."""
    return None if value is None else format(int(value) & 0xFFFFFFFFFFFFFFFF, "016x")


def phash_from_hex(text: str | int | None) -> int | None:
    if text is None:
        return None
    if isinstance(text, int):
        return text
    try:
        return int(text, 16)
    except (ValueError, TypeError):
        return None


def _resize_nearest(gray: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = gray.shape
    yi = (np.linspace(0, h - 1, height)).astype(np.int32)
    xi = (np.linspace(0, w - 1, width)).astype(np.int32)
    return gray[yi][:, xi]


# --- faces ----------------------------------------------------------------

def detect_faces(rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Face boxes as (x, y, w, h). Empty when no backend is available."""
    return _faces.detect(rgb)


# --- aggregate ------------------------------------------------------------

def measure(rgb: np.ndarray, prev_gray: np.ndarray | None, *, want_faces: bool) -> dict[str, Any]:
    """All measurements for one analysis frame."""
    gray = luma(rgb)
    hist = gray_histogram(gray)
    exposure = exposure_stats(gray, hist)
    comp, cx, cy = thirds_score(gray)

    motion = 0.0
    if prev_gray is not None and prev_gray.shape == gray.shape:
        motion = float(np.mean(np.abs(gray - prev_gray)))

    out: dict[str, Any] = {
        "lap_var": laplacian_variance(gray),
        "tenengrad": tenengrad(gray),
        "edge_density": edge_density(gray),
        "colorfulness": colorfulness(rgb),
        "colour_temp": colour_temperature(rgb),
        "composition": comp,
        "centroid": [round(cx, 3), round(cy, 3)],
        "motion": motion,
        "phash": dhash(gray),
        **exposure,
    }

    apply_faces(out, rgb, gray.shape, detect_faces(rgb) if want_faces else [])
    out["_gray"] = gray
    out["_hist"] = hist
    return out


def apply_faces(out: dict[str, Any], rgb: np.ndarray,
                shape: tuple[int, int], faces: list[tuple[int, int, int, int]]) -> dict[str, Any]:
    """Write face-derived fields into a measurement dict (in place)."""
    h, w = shape
    out["face_count"] = len(faces)
    if faces:
        biggest = max(faces, key=lambda f: f[2] * f[3])
        out["face_height_frac"] = round(biggest[3] / max(h, 1), 4)
        out["face_area_frac"] = round((biggest[2] * biggest[3]) / max(h * w, 1), 4)
        out["face_center"] = [
            round((biggest[0] + biggest[2] / 2) / max(w, 1), 3),
            round((biggest[1] + biggest[3] / 2) / max(h, 1), 3),
        ]
    else:
        out["face_height_frac"] = 0.0
        out["face_area_frac"] = 0.0
        out["face_center"] = None
    return out
