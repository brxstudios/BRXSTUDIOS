"""Turn thousands of scored frames into a short list worth extracting.

Four filters, applied in order:
  1. hard gates      - anything the analysis pass already rejected, plus a score floor
  2. per-shot quota  - the best N frames of each shot, spaced apart in time
  3. per-clip quota  - the best N of whatever survives, so one long take cannot
                       swamp the selection
  4. dedupe          - perceptual-hash clustering, within and then across clips
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Iterable

from .config import Config
from .metrics import hamming, phash_from_hex

log = logging.getLogger("stillharvest")


def _dedupe(rows: Iterable[dict[str, Any]], distance: int) -> list[dict[str, Any]]:
    """Keep the highest-scoring frame of each near-identical cluster.

    Greedy by score: a frame is kept unless it looks like something already kept.
    """
    kept: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: -r["score"]):
        phash = phash_from_hex(row.get("phash"))
        row["phash"] = phash
        if phash is None:
            kept.append(row)
            continue
        if any(
            k.get("phash") is not None and hamming(phash, k["phash"]) <= distance
            for k in kept
        ):
            continue
        kept.append(row)
    return kept


def _spaced(rows: list[dict[str, Any]], limit: int, min_gap: float) -> list[dict[str, Any]]:
    """Best-first pick that refuses two keepers closer than ``min_gap`` seconds."""
    chosen: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: -r["score"]):
        if len(chosen) >= limit:
            break
        if all(abs(row["t"] - c["t"]) >= min_gap for c in chosen):
            chosen.append(row)
    return chosen


def select_clip(conn: sqlite3.Connection, clip_id: int, cfg: Config) -> list[int]:
    """Choose the keepers for one clip and return their frame ids."""
    rows = [
        dict(r) for r in conn.execute(
            "SELECT id, t, shot, score, phash FROM frames "
            "WHERE clip_id=? AND rejected IS NULL AND score >= ?",
            (clip_id, cfg.min_score),
        )
    ]
    if not rows:
        return []

    by_shot: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_shot.setdefault(row["shot"], []).append(row)

    survivors: list[dict[str, Any]] = []
    for shot_rows in by_shot.values():
        survivors.extend(_spaced(shot_rows, cfg.per_shot, cfg.min_separation))

    survivors = _dedupe(survivors, cfg.dedupe_distance)
    survivors = sorted(survivors, key=lambda r: -r["score"])[: max(1, cfg.per_clip)]
    return [r["id"] for r in survivors]


def select_all(conn: sqlite3.Connection, cfg: Config) -> dict[str, int]:
    """Run selection across the whole catalog. Returns a small summary."""
    conn.execute("UPDATE frames SET selected=0")
    clip_ids = [int(r["id"]) for r in conn.execute(
        "SELECT id FROM clips WHERE status='analyzed' ORDER BY path"
    )]

    picked: list[int] = []
    for clip_id in clip_ids:
        picked.extend(select_clip(conn, clip_id, cfg))

    before_global = len(picked)
    if picked:
        rows = [
            dict(r) for r in conn.execute(
                "SELECT id, t, score, phash FROM frames WHERE id IN (%s)"
                % ",".join("?" * len(picked)),
                picked,
            )
        ]
        # A second dedupe pass across clips catches repeated setups and B-roll
        # covered twice from the same angle.
        rows = _dedupe(rows, max(1, cfg.dedupe_distance - 2))
        if cfg.global_limit > 0:
            rows = sorted(rows, key=lambda r: -r["score"])[: cfg.global_limit]
        picked = [r["id"] for r in rows]

    if picked:
        conn.executemany(
            "UPDATE frames SET selected=1 WHERE id=?", [(i,) for i in picked]
        )
    conn.commit()
    return {
        "clips": len(clip_ids),
        "per_clip_picked": before_global,
        "selected": len(picked),
        "dropped_cross_clip": before_global - len(picked),
    }
