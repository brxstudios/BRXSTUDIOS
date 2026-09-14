"""Assign categories to extracted stills.

Two tiers, and the first always runs:

* **Rules** - derived from measurements already in the catalog (face size and
  count, tonal spread, motion, aspect). Free, instant, offline, and enough to
  file a shoot into portraits / groups / details / environments.
* **Claude vision** (opt-in, ``--ai``) - sends thumbnails of the *selected*
  stills only and gets back a semantic category, a caption and keywords. This
  is what turns "Close-Up" into "Interview" or "Behind The Scenes".
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from .config import Config

log = logging.getLogger("stillharvest")


# --------------------------------------------------------------------------
# tier 1: rules over the measurements we already have
# --------------------------------------------------------------------------

def shot_type(metrics: dict[str, Any]) -> str:
    """Standard coverage sizes, inferred from how much frame height a face fills."""
    faces = int(metrics.get("face_count") or 0)
    frac = float(metrics.get("face_height_frac") or 0.0)
    if faces and frac > 0:
        if frac >= 0.55:
            return "Extreme Close-Up"
        if frac >= 0.30:
            return "Close-Up"
        if frac >= 0.17:
            return "Medium Close-Up"
        if frac >= 0.09:
            return "Medium"
        if frac >= 0.035:
            return "Wide"
        return "Extreme Wide"
    # No face to measure against - fall back to how busy the frame is.
    return "Detail" if float(metrics.get("edge_density") or 0.0) >= 0.22 else "Environment"


def people(metrics: dict[str, Any]) -> str:
    count = int(metrics.get("face_count") or 0)
    if count <= 0:
        return "None"
    if count == 1:
        return "Solo"
    if count == 2:
        return "Duo"
    return "Small Group" if count <= 5 else "Crowd"


def lighting(metrics: dict[str, Any]) -> str:
    mean = float(metrics.get("mean") or 0.0)
    spread = float(metrics.get("p95") or 0.0) - float(metrics.get("p05") or 0.0)
    crushed = float(metrics.get("crushed_low") or 0.0)
    if mean < 70 and crushed > 0.22:
        return "Low Key"
    if mean > 165 and float(metrics.get("clipped_high") or 0.0) < 0.05:
        return "High Key"
    if spread > 195:
        return "High Contrast"
    if spread < 90:
        return "Flat / Log"
    return "Balanced"


def colour(metrics: dict[str, Any]) -> str:
    if float(metrics.get("colorfulness") or 0.0) < 8.0:
        return "Monochrome"
    return str(metrics.get("colour_temp") or "neutral").capitalize()


def motion_class(metrics: dict[str, Any]) -> str:
    return "Action" if float(metrics.get("motion") or 0.0) >= 18.0 else "Static"


def orientation(width: int, height: int) -> str:
    if height == 0:
        return "Unknown"
    ratio = width / height
    if ratio > 1.15:
        return "Landscape"
    if ratio < 0.87:
        return "Portrait"
    return "Square"


def rule_category(metrics: dict[str, Any]) -> str:
    """A single best-guess bucket, used until (or instead of) the AI pass."""
    faces = int(metrics.get("face_count") or 0)
    size = shot_type(metrics)
    moving = motion_class(metrics) == "Action"

    if faces >= 6:
        return "Crowd"
    if faces >= 3:
        return "Group"
    if faces == 2:
        return "Group"
    if faces == 1:
        if size in ("Extreme Close-Up", "Close-Up", "Medium Close-Up"):
            return "Portrait"
        return "Action" if moving else "Candid"
    if moving:
        return "Action"
    if float(metrics.get("edge_density") or 0.0) >= 0.26:
        return "Detail"
    return "Environment"


def rank_ratings(scores: Sequence[float]) -> list[str]:
    """Rate stills relative to this shoot: top 12% hero, next 33% select."""
    if not scores:
        return []
    ordered = sorted(range(len(scores)), key=lambda i: -scores[i])
    ratings = ["usable"] * len(scores)
    hero_cut = max(1, int(round(len(scores) * 0.12)))
    select_cut = max(hero_cut, int(round(len(scores) * 0.45)))
    for rank, index in enumerate(ordered):
        ratings[index] = "hero" if rank < hero_cut else ("select" if rank < select_cut else "usable")
    return ratings


def tag_still(metrics: dict[str, Any], width: int, height: int) -> dict[str, str]:
    return {
        "shot_type": shot_type(metrics),
        "people": people(metrics),
        "lighting": lighting(metrics),
        "colour": colour(metrics),
        "motion": motion_class(metrics),
        "orientation": orientation(width, height),
        "category": rule_category(metrics),
    }


# --------------------------------------------------------------------------
# tier 2: Claude vision
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are triaging still frames pulled from video footage of a film shoot, \
deciding how each one should be filed in a photo library.

For every image you are given, return one entry with:
  category - exactly one label from the supplied list, whichever fits best
  caption  - one short factual sentence describing what is pictured
  keywords - 3 to 6 lowercase search terms (subjects, setting, mood)
  quality  - 0.0 to 1.0, how usable this is as a standalone photograph, \
judging focus, framing, expression and exposure
  usable   - false if it is a transition, a blurred frame, an out-of-focus \
frame, a slate/colour chart, or otherwise not worth keeping

Describe only what is actually visible. Return entries in the same order as \
the images, one per image."""

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "caption": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "quality": {"type": "number"},
                    "usable": {"type": "boolean"},
                },
                "required": ["category", "caption", "keywords", "quality", "usable"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["entries"],
    "additionalProperties": False,
}


def encode_image(path: str | Path, width: int) -> bytes | None:
    """Downscale an image to ``width`` and return JPEG bytes, via FFmpeg."""
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
         "-vf", f"scale='min({width},iw)':-2:flags=area",
         "-frames:v", "1", "-q:v", "4", "-f", "mjpeg", "-"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0 or not proc.stdout:
        log.warning("could not encode %s for the AI pass", path)
        return None
    return proc.stdout


def build_batch_message(images: Sequence[bytes], categories: Sequence[str]) -> list[dict]:
    """One user turn holding every image in the batch, each announced by index."""
    content: list[dict[str, Any]] = [{
        "type": "text",
        "text": (
            "Categories to choose from:\n"
            + "\n".join(f"- {c}" for c in categories)
            + f"\n\nClassify the following {len(images)} image(s), in order."
        ),
    }]
    for index, blob in enumerate(images, start=1):
        content.append({"type": "text", "text": f"Image {index}:"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(blob).decode("ascii"),
            },
        })
    return [{"role": "user", "content": content}]


def _extract_entries(response: Any) -> list[dict[str, Any]]:
    text = next(
        (b.text for b in response.content if getattr(b, "type", None) == "text"), None
    )
    if not text:
        return []
    try:
        return list(json.loads(text).get("entries") or [])
    except (json.JSONDecodeError, AttributeError):
        log.warning("AI returned unparseable JSON; skipping this batch")
        return []


def classify_batch(client: Any, images: Sequence[bytes], cfg: Config) -> list[dict[str, Any]]:
    """Classify one batch of images. Returns one entry per image (best effort)."""
    request = dict(
        model=cfg.ai_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=build_batch_message(images, cfg.categories),
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
    )
    try:
        response = client.beta.messages.create(
            **request,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except Exception as exc:
        # Older accounts may not have the server-side fallback beta enabled.
        log.debug("beta call failed (%s); retrying without refusal fallbacks", exc)
        response = client.messages.create(**request)

    if getattr(response, "stop_reason", None) == "refusal":
        log.warning("model declined to classify a batch of %d images", len(images))
        return []
    return _extract_entries(response)


def normalise_entry(entry: dict[str, Any], categories: Sequence[str]) -> dict[str, Any]:
    """Coerce a model entry into catalog columns, snapping the category to the list."""
    raw = str(entry.get("category") or "").strip()
    match = next((c for c in categories if c.lower() == raw.lower()), None)
    if match is None:
        match = next((c for c in categories if raw and raw.lower() in c.lower()), None)
    keywords = entry.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    try:
        quality = max(0.0, min(1.0, float(entry.get("quality", 0.0))))
    except (TypeError, ValueError):
        quality = 0.0
    return {
        "ai_category": match or (raw or None),
        "ai_caption": str(entry.get("caption") or "").strip() or None,
        "ai_keywords": ", ".join(str(k).strip().lower() for k in keywords if str(k).strip()) or None,
        "ai_quality": quality,
        "usable": bool(entry.get("usable", True)),
    }


def estimate_cost(count: int, cfg: Config) -> float:
    """Rough USD estimate so a run cannot surprise anyone. Opus 5 input pricing."""
    per_image_tokens = (cfg.ai_thumb_width * cfg.ai_thumb_width * 0.56) / 750.0
    batches = max(1, (count + cfg.ai_batch_size - 1) // cfg.ai_batch_size)
    input_tokens = count * per_image_tokens + batches * 400
    output_tokens = count * 90
    return round(input_tokens / 1e6 * 5.0 + output_tokens / 1e6 * 25.0, 4)


def chunked(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), max(1, size)):
        yield items[start:start + max(1, size)]
