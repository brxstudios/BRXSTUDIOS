"""SQLite catalog. Every stage writes here so a run can be stopped and resumed."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from .metrics import phash_to_hex

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS clips (
    id            INTEGER PRIMARY KEY,
    path          TEXT UNIQUE NOT NULL,
    rel_path      TEXT,
    shoot         TEXT,
    reel          TEXT,
    size_bytes    INTEGER,
    mtime         REAL,
    duration      REAL,
    fps           REAL,
    width         INTEGER,
    height        INTEGER,
    rotation      INTEGER DEFAULT 0,
    codec         TEXT,
    pix_fmt       TEXT,
    bit_depth     INTEGER,
    captured_at   TEXT,
    camera        TEXT,
    probe_json    TEXT,
    status        TEXT DEFAULT 'new',   -- new|analyzed|skipped|error
    note          TEXT,
    shots         INTEGER DEFAULT 0,
    candidates    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS frames (
    id         INTEGER PRIMARY KEY,
    clip_id    INTEGER NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    t          REAL NOT NULL,        -- seconds into the clip
    shot       INTEGER NOT NULL,
    score      REAL NOT NULL,
    phash      TEXT,          -- 16-char hex; see metrics.phash_to_hex
    metrics    TEXT,                 -- json blob of raw measurements
    rejected   TEXT,                 -- null = viable, else reason
    selected   INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_frames_clip  ON frames(clip_id);
CREATE INDEX IF NOT EXISTS idx_frames_score ON frames(score DESC);

CREATE TABLE IF NOT EXISTS stills (
    id           INTEGER PRIMARY KEY,
    frame_id     INTEGER UNIQUE NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    clip_id      INTEGER NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    t            REAL NOT NULL,
    timecode     TEXT,
    filename     TEXT,
    path         TEXT,
    thumb        TEXT,
    width        INTEGER,
    height       INTEGER,
    score        REAL,
    rating       TEXT,              -- hero|select|usable
    shot_type    TEXT,
    people       TEXT,
    lighting     TEXT,
    colour       TEXT,
    motion       TEXT,
    orientation  TEXT,
    category     TEXT,
    ai_caption   TEXT,
    ai_keywords  TEXT,
    ai_category  TEXT,
    ai_quality   REAL
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def set_meta(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )


def get_meta(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def upsert_clip(conn: sqlite3.Connection, clip: dict) -> int:
    cols = [k for k in clip if k != "id"]
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "path")
    sql = (
        f"INSERT INTO clips ({','.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(path) DO UPDATE SET {updates}"
    )
    conn.execute(sql, [clip[c] for c in cols])
    row = conn.execute("SELECT id FROM clips WHERE path=?", (clip["path"],)).fetchone()
    return int(row["id"])


def replace_frames(conn: sqlite3.Connection, clip_id: int, rows: Iterable[dict]) -> int:
    conn.execute("DELETE FROM frames WHERE clip_id=?", (clip_id,))
    payload = [
        (clip_id, r["t"], r["shot"], r["score"], phash_to_hex(r.get("phash")),
         json.dumps(r.get("metrics", {})), r.get("rejected"))
        for r in rows
    ]
    conn.executemany(
        "INSERT INTO frames (clip_id,t,shot,score,phash,metrics,rejected) "
        "VALUES (?,?,?,?,?,?,?)",
        payload,
    )
    return len(payload)


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    def one(sql: str, *args) -> int:
        row = conn.execute(sql, args).fetchone()
        return int(row[0]) if row else 0

    return {
        "clips": one("SELECT COUNT(*) FROM clips"),
        "analyzed": one("SELECT COUNT(*) FROM clips WHERE status='analyzed'"),
        "skipped": one("SELECT COUNT(*) FROM clips WHERE status IN ('skipped','error')"),
        "candidates": one("SELECT COUNT(*) FROM frames WHERE rejected IS NULL"),
        "selected": one("SELECT COUNT(*) FROM frames WHERE selected=1"),
        "stills": one("SELECT COUNT(*) FROM stills"),
    }
