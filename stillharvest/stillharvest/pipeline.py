"""Stage drivers. Each one is resumable: state lives in the SQLite catalog."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from . import categorize as cat
from . import db as dbm
from . import extract as ex
from . import organize as org
from .analyze import analyze_clip
from .config import Config
from .probe import classify_unsupported, iter_media_files, probe_clip
from .select import select_all
from .util import human_duration, timecode

log = logging.getLogger("stillharvest")


# --------------------------------------------------------------------------
# progress
# --------------------------------------------------------------------------

class Progress:
    """Single-line progress with a rate and an ETA; quiet when piped to a file."""

    def __init__(self, total: int, label: str, *, enabled: bool = True) -> None:
        self.total = max(0, total)
        self.label = label
        self.done = 0
        self.started = time.monotonic()
        self.enabled = enabled and sys.stderr.isatty()
        self._last = 0.0

    def advance(self, step: int = 1, suffix: str = "") -> None:
        self.done += step
        now = time.monotonic()
        if not self.enabled or (now - self._last < 0.15 and self.done < self.total):
            return
        self._last = now
        elapsed = now - self.started
        rate = self.done / elapsed if elapsed > 0 else 0.0
        remaining = (self.total - self.done) / rate if rate > 0 else 0.0
        pct = (100.0 * self.done / self.total) if self.total else 100.0
        sys.stderr.write(
            f"\r  {self.label}: {self.done}/{self.total} ({pct:4.1f}%) "
            f"{rate:.1f}/s  ETA {human_duration(remaining)}  {suffix[:44]:<44}"
        )
        sys.stderr.flush()

    def close(self) -> None:
        if self.enabled:
            sys.stderr.write("\r" + " " * 118 + "\r")
            sys.stderr.flush()


def worker_count(requested: int) -> int:
    if requested and requested > 0:
        return requested
    return max(1, (os.cpu_count() or 2) - 1)


# --------------------------------------------------------------------------
# multiprocessing entry points (module level so they pickle under 'spawn')
# --------------------------------------------------------------------------

def _analyze_task(payload: tuple[dict, dict, int]) -> tuple[int, dict]:
    clip, cfg_dict, threads = payload
    cfg = Config.from_dict(cfg_dict)
    try:
        result = analyze_clip(clip, cfg, threads=threads)
    except Exception as exc:                      # one bad file must not stop the run
        result = {"frames": [], "shots": 0, "note": f"{type(exc).__name__}: {exc}"}
    return int(clip["id"]), result


def _extract_task(payload: tuple[dict, dict, dict]) -> dict:
    clip, frame, cfg_dict = payload
    cfg = Config.from_dict(cfg_dict)
    try:
        refined = ex.refine_timestamp(clip, float(frame["t"]), cfg)
        name = ex.still_filename(clip, refined, float(frame["score"]), ex.extension_for(cfg))
        dest = Path(frame["stills_dir"]) / name
        thumb = Path(frame["thumbs_dir"]) / (Path(name).stem + ".jpg")
        ok = ex.extract_still(clip, refined, dest, thumb, cfg)
        if not ok:
            return {"frame_id": frame["id"], "ok": False}
        width, height = ex.still_dimensions(clip, cfg)
        return {
            "frame_id": frame["id"], "clip_id": int(clip["id"]), "ok": True,
            "t": refined, "timecode": timecode(refined, float(clip.get("fps") or 25.0)),
            "filename": name, "path": str(dest),
            "thumb": str(thumb) if thumb.is_file() else None,
            "width": width, "height": height, "score": float(frame["score"]),
        }
    except Exception as exc:
        log.debug("extract task failed: %s", exc)
        return {"frame_id": frame["id"], "ok": False}


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------

def stage_scan(conn: sqlite3.Connection, root: Path, cfg: Config, *,
               quiet: bool = False, rescan: bool = False) -> dict:
    """Index every video file under ``root``.

    Clips already *analysed*, whose size and mtime are unchanged, are left alone
    and not even re-probed, so scanning a drive a second time costs a stat per
    file instead of an ffprobe and never discards work already done. Files that
    were skipped or errored are always re-probed, so relaxing a gate such as
    ``--min-file-size`` re-admits them. Pass ``rescan=True`` to re-probe
    everything.
    """
    files = list(iter_media_files(root, cfg))
    known = {
        str(r["path"]): (r["size_bytes"], r["mtime"], r["status"])
        for r in conn.execute("SELECT path, size_bytes, mtime, status FROM clips")
    }

    progress = Progress(len(files), "scanning", enabled=not quiet)
    added = skipped = unchanged = 0
    total_bytes = 0.0
    total_seconds = 0.0

    with dbm.transaction(conn):
        for path in files:
            try:
                stat = path.stat()
            except OSError as exc:
                log.warning("cannot stat %s: %s", path, exc)
                progress.advance(suffix=path.name)
                continue

            previous = known.get(str(path))
            if (
                not rescan and previous is not None
                and previous[0] == stat.st_size
                and previous[1] is not None and abs(float(previous[1]) - stat.st_mtime) < 1e-6
                # Only completed analysis is worth preserving. Anything skipped
                # or errored is re-probed, so changing a gate (--min-file-size,
                # --min-duration) re-admits files it previously excluded.
                and previous[2] == "analyzed"
            ):
                unchanged += 1
                progress.advance(suffix=path.name)
                continue

            try:
                row = probe_clip(path, root, cfg)
            except OSError as exc:
                log.warning("cannot read %s: %s", path, exc)
                progress.advance(suffix=path.name)
                continue
            dbm.upsert_clip(conn, row)
            if row["status"] == "new":
                added += 1
                total_bytes += row["size_bytes"] or 0
                total_seconds += row["duration"] or 0
            else:
                skipped += 1
            progress.advance(suffix=path.name)
        dbm.set_meta(conn, "root", str(root))
    progress.close()

    unsupported = classify_unsupported(root, cfg)
    if unsupported:
        dbm.set_meta(conn, "unsupported", [str(p) for p in unsupported])
        conn.commit()

    return {
        "found": len(files), "usable": added, "skipped": skipped,
        "unchanged": unchanged, "unsupported": len(unsupported),
        "bytes": total_bytes, "seconds": total_seconds,
    }


def stage_analyze(conn: sqlite3.Connection, cfg: Config, *,
                  workers: int = 0, reanalyze: bool = False, quiet: bool = False) -> dict:
    """Measure every sampled frame of every clip that still needs it."""
    where = "status='new'" if not reanalyze else "status IN ('new','analyzed')"
    clips = [dict(r) for r in conn.execute(
        f"SELECT * FROM clips WHERE {where} ORDER BY size_bytes DESC"
    )]
    if not clips:
        return {"clips": 0, "frames": 0, "candidates": 0}

    cfg_dict = cfg.to_dict()
    n_workers = min(worker_count(workers), len(clips))
    # Decoding is the bottleneck and scales almost linearly with threads, so
    # hand the spare cores to FFmpeg when there are fewer clips than workers
    # (a handful of long takes would otherwise leave most of the CPU idle).
    decode_threads = max(1, (os.cpu_count() or 2) // max(1, n_workers))
    progress = Progress(len(clips), "analysing", enabled=not quiet)
    total_frames = total_candidates = 0

    def commit(clip_id: int, result: dict) -> None:
        nonlocal total_frames, total_candidates
        rows = result["frames"]
        with dbm.transaction(conn):
            dbm.replace_frames(conn, clip_id, rows)
            viable = sum(1 for r in rows if r["rejected"] is None)
            conn.execute(
                "UPDATE clips SET status=?, note=?, shots=?, candidates=? WHERE id=?",
                ("analyzed" if rows else "skipped", result.get("note"),
                 result.get("shots", 0), viable, clip_id),
            )
        total_frames += len(rows)
        total_candidates += viable

    if n_workers == 1:
        for clip in clips:
            clip_id, result = _analyze_task((clip, cfg_dict, decode_threads))
            commit(clip_id, result)
            progress.advance(suffix=Path(clip["path"]).name)
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(_analyze_task, (clip, cfg_dict, decode_threads)): clip
                for clip in clips
            }
            for future in as_completed(futures):
                clip = futures[future]
                try:
                    clip_id, result = future.result()
                except Exception as exc:
                    log.warning("analysis crashed for %s: %s", clip["path"], exc)
                    conn.execute(
                        "UPDATE clips SET status='error', note=? WHERE id=?",
                        (str(exc)[:200], clip["id"]),
                    )
                    conn.commit()
                    progress.advance(suffix=Path(clip["path"]).name)
                    continue
                commit(clip_id, result)
                progress.advance(suffix=Path(clip["path"]).name)
    progress.close()
    return {"clips": len(clips), "frames": total_frames, "candidates": total_candidates}


def stage_select(conn: sqlite3.Connection, cfg: Config) -> dict:
    return select_all(conn, cfg)


def stage_extract(conn: sqlite3.Connection, cfg: Config, out_dir: Path, *,
                  workers: int = 0, quiet: bool = False) -> dict:
    """Export a full-resolution still for every selected frame."""
    dirs = org.ensure_dirs(out_dir)
    # Alias every column explicitly: `f.id` and `c.id` would otherwise collide
    # and the frame id would silently become the clip id.
    rows = [dict(r) for r in conn.execute(
        "SELECT f.id AS frame_id, f.t AS t, f.score AS score, "
        "       c.id AS clip_id, c.path AS path, c.width AS width, "
        "       c.height AS height, c.rotation AS rotation, c.fps AS fps, "
        "       c.duration AS duration, c.shoot AS shoot, c.reel AS reel "
        "FROM frames f JOIN clips c ON c.id = f.clip_id "
        "WHERE f.selected=1 AND f.id NOT IN (SELECT frame_id FROM stills) "
        "ORDER BY c.path, f.t"
    )]
    if not rows:
        return {"extracted": 0, "failed": 0}

    cfg_dict = cfg.to_dict()
    tasks = []
    for row in rows:
        clip = {
            "id": row["clip_id"], "path": row["path"],
            "width": row["width"], "height": row["height"],
            "rotation": row["rotation"], "fps": row["fps"],
            "duration": row["duration"], "shoot": row["shoot"], "reel": row["reel"],
        }
        frame = {
            "id": row["frame_id"], "t": row["t"], "score": row["score"],
            "stills_dir": str(dirs["stills"] / org._bucket(row["shoot"], "footage")),
            "thumbs_dir": str(dirs["thumbs"]),
        }
        tasks.append((clip, frame, cfg_dict))

    n_workers = min(worker_count(workers), len(tasks))
    progress = Progress(len(tasks), "extracting", enabled=not quiet)
    extracted = failed = 0

    def store(result: dict) -> None:
        nonlocal extracted, failed
        if not result.get("ok"):
            failed += 1
            return
        conn.execute(
            "INSERT OR REPLACE INTO stills "
            "(frame_id, clip_id, t, timecode, filename, path, thumb, width, height, score) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (result["frame_id"], result["clip_id"], result["t"], result["timecode"],
             result["filename"], result["path"], result["thumb"],
             result["width"], result["height"], result["score"]),
        )
        extracted += 1

    if n_workers == 1:
        for task in tasks:
            store(_extract_task(task))
            progress.advance()
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_extract_task, task) for task in tasks]
            for future in as_completed(futures):
                try:
                    store(future.result())
                except Exception as exc:
                    log.warning("extract crashed: %s", exc)
                    failed += 1
                progress.advance()
    conn.commit()
    progress.close()
    return {"extracted": extracted, "failed": failed}


def stage_tag(conn: sqlite3.Connection) -> dict:
    """Apply the offline rule-based tags to every extracted still."""
    rows = list(conn.execute(
        "SELECT s.id, s.width, s.height, s.score, f.metrics "
        "FROM stills s JOIN frames f ON f.id = s.frame_id"
    ))
    if not rows:
        return {"tagged": 0}

    ratings = cat.rank_ratings([float(r["score"] or 0.0) for r in rows])
    payload = []
    for row, rating in zip(rows, ratings):
        try:
            metrics = json.loads(row["metrics"] or "{}")
        except json.JSONDecodeError:
            metrics = {}
        tags = cat.tag_still(metrics, int(row["width"] or 0), int(row["height"] or 0))
        payload.append((
            tags["shot_type"], tags["people"], tags["lighting"], tags["colour"],
            tags["motion"], tags["orientation"], tags["category"], rating, row["id"],
        ))
    conn.executemany(
        "UPDATE stills SET shot_type=?, people=?, lighting=?, colour=?, motion=?, "
        "orientation=?, category=?, rating=? WHERE id=?",
        payload,
    )
    conn.commit()
    return {"tagged": len(payload)}


def stage_ai(conn: sqlite3.Connection, cfg: Config, *,
             limit: int = 0, quiet: bool = False) -> dict:
    """Classify stills with Claude vision. Requires the `anthropic` package."""
    try:
        import anthropic  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "The AI pass needs the Anthropic SDK: pip install anthropic"
        ) from exc

    rows = [dict(r) for r in conn.execute(
        "SELECT id, path, thumb FROM stills WHERE ai_category IS NULL ORDER BY score DESC"
    )]
    if limit > 0:
        rows = rows[:limit]
    if not rows:
        return {"classified": 0, "cost_estimate": 0.0}

    client = anthropic.Anthropic()
    progress = Progress(len(rows), "classifying", enabled=not quiet)
    classified = 0

    for batch in cat.chunked(rows, cfg.ai_batch_size):
        images, keep = [], []
        for row in batch:
            source = row["thumb"] or row["path"]
            blob = cat.encode_image(source, cfg.ai_thumb_width) if source else None
            if blob:
                images.append(blob)
                keep.append(row)
        if not images:
            progress.advance(len(batch))
            continue

        try:
            entries = cat.classify_batch(client, images, cfg)
        except Exception as exc:
            log.warning("AI batch failed: %s", exc)
            progress.advance(len(batch))
            continue

        for row, entry in zip(keep, entries):
            fields = cat.normalise_entry(entry, cfg.categories)
            conn.execute(
                "UPDATE stills SET ai_category=?, ai_caption=?, ai_keywords=?, ai_quality=? "
                "WHERE id=?",
                (fields["ai_category"], fields["ai_caption"],
                 fields["ai_keywords"], fields["ai_quality"], row["id"]),
            )
            if not fields["usable"]:
                conn.execute("UPDATE stills SET rating='rejected' WHERE id=?", (row["id"],))
            classified += 1
        conn.commit()
        progress.advance(len(batch))

    progress.close()
    return {"classified": classified, "cost_estimate": cat.estimate_cost(len(rows), cfg)}
