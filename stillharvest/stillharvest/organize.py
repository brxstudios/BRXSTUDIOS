"""Lay the extracted stills out on disk and write the manifests.

One copy of each still lives under ``stills/``. Everything in ``catalog/`` is a
link into that copy, so a still can appear under several categories without
costing extra disk. Symlinks are the default; ``--link copy`` produces a tree
that survives being moved to another drive or handed to a client.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .util import slugify

log = logging.getLogger("stillharvest")

MANIFEST_COLUMNS = [
    "filename", "path", "shoot", "reel", "source_clip", "timecode", "t_seconds",
    "score", "rating", "category", "ai_category", "shot_type", "people",
    "lighting", "colour", "motion", "orientation", "width", "height",
    "ai_caption", "ai_keywords", "ai_quality",
]


def project_dirs(out_dir: str | Path) -> dict[str, Path]:
    root = Path(out_dir)
    return {
        "root": root,
        "stills": root / "stills",
        "thumbs": root / "thumbs",
        "catalog": root / "catalog",
        "db": root / "harvest.db",
        "config": root / "config.json",
        "manifest_csv": root / "manifest.csv",
        "manifest_json": root / "manifest.json",
        "report": root / "index.html",
    }


def ensure_dirs(out_dir: str | Path) -> dict[str, Path]:
    dirs = project_dirs(out_dir)
    for key in ("root", "stills", "thumbs", "catalog"):
        dirs[key].mkdir(parents=True, exist_ok=True)
    return dirs


def place(src: Path, dst: Path, mode: str) -> bool:
    """Link (or copy) ``src`` to ``dst``, degrading gracefully.

    Symlinks need elevated rights on Windows and do not exist on some network
    shares, so every mode falls back rather than aborting the run.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return True
    order = {
        "symlink": ("symlink", "hardlink", "copy"),
        "hardlink": ("hardlink", "symlink", "copy"),
        "copy": ("copy",),
    }.get(mode, ("symlink", "hardlink", "copy"))

    for attempt in order:
        try:
            if attempt == "symlink":
                os.symlink(os.path.relpath(src, dst.parent), dst)
            elif attempt == "hardlink":
                os.link(src, dst)
            else:
                shutil.copy2(src, dst)
            return True
        except (OSError, NotImplementedError, shutil.Error):
            continue
    log.warning("could not place %s at %s", src.name, dst)
    return False


def _bucket(value: Any, fallback: str = "Unsorted") -> str:
    text = str(value).strip() if value else ""
    if not text:
        return fallback
    return slugify(text, maxlen=40) or fallback


def build_catalog(conn: sqlite3.Connection, out_dir: str | Path, link_mode: str) -> dict[str, int]:
    """(Re)build the browsable category trees from the ``stills`` table."""
    dirs = project_dirs(out_dir)
    catalog = dirs["catalog"]
    if catalog.exists():
        shutil.rmtree(catalog)
    catalog.mkdir(parents=True, exist_ok=True)

    rows = list(conn.execute(
        "SELECT s.*, c.shoot AS shoot, c.reel AS reel, c.path AS clip_path "
        "FROM stills s JOIN clips c ON c.id = s.clip_id "
        "WHERE s.path IS NOT NULL ORDER BY s.score DESC"
    ))
    made = 0
    for row in rows:
        src = Path(row["path"])
        if not src.is_file():
            continue
        name = row["filename"] or src.name
        # Prefer the model's category when the AI pass ran; fall back to rules.
        category = row["ai_category"] or row["category"] or "Unsorted"
        targets = [
            catalog / "by-category" / _bucket(category) / name,
            catalog / "by-shot-type" / _bucket(row["shot_type"]) / name,
            catalog / "by-rating" / _bucket(row["rating"], "usable") / name,
            catalog / "by-shoot" / _bucket(row["shoot"], "footage") / _bucket(category) / name,
        ]
        for target in targets:
            if place(src, target, link_mode):
                made += 1
    return {"stills": len(rows), "links": made}


def manifest_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT s.*, c.shoot AS shoot, c.reel AS reel, c.path AS clip_path "
        "FROM stills s JOIN clips c ON c.id = s.clip_id ORDER BY s.score DESC"
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({
            "filename": row["filename"],
            "path": row["path"],
            "shoot": row["shoot"],
            "reel": row["reel"],
            "source_clip": row["clip_path"],
            "timecode": row["timecode"],
            "t_seconds": round(float(row["t"] or 0.0), 3),
            "score": row["score"],
            "rating": row["rating"],
            "category": row["category"],
            "ai_category": row["ai_category"],
            "shot_type": row["shot_type"],
            "people": row["people"],
            "lighting": row["lighting"],
            "colour": row["colour"],
            "motion": row["motion"],
            "orientation": row["orientation"],
            "width": row["width"],
            "height": row["height"],
            "ai_caption": row["ai_caption"],
            "ai_keywords": row["ai_keywords"],
            "ai_quality": row["ai_quality"],
        })
    return out


def write_manifests(conn: sqlite3.Connection, out_dir: str | Path) -> dict[str, Any]:
    dirs = project_dirs(out_dir)
    rows = manifest_rows(conn)

    with dirs["manifest_csv"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    dirs["manifest_json"].write_text(
        json.dumps({"stills": rows, "count": len(rows)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"rows": len(rows), "csv": str(dirs["manifest_csv"]), "json": str(dirs["manifest_json"])}


def category_summary(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT COALESCE(ai_category, category, 'Unsorted') AS cat, COUNT(*) AS n "
        "FROM stills GROUP BY cat ORDER BY n DESC"
    )
    return [(str(r["cat"]), int(r["n"])) for r in rows]
