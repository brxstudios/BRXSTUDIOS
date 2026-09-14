"""Tunable settings. Everything a colourist or DIT might want to change lives here."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

VIDEO_EXTENSIONS = (
    ".mov", ".mp4", ".m4v", ".mxf", ".avi", ".mts", ".m2ts", ".mkv",
    ".wmv", ".insv", ".lrv", ".avchd", ".3gp", ".webm", ".dv", ".ts", ".vob",
)

# Formats FFmpeg cannot decode without vendor SDKs. We surface these as skipped
# rather than silently ignoring them, so nothing on the drive goes unaccounted for.
UNSUPPORTED_EXTENSIONS = (".braw", ".r3d", ".ari", ".arx", ".crm", ".cine")

DEFAULT_CATEGORIES = [
    "Portrait",
    "Group",
    "Candid",
    "Interview",
    "Detail",
    "Environment",
    "Action",
    "Product",
    "Behind The Scenes",
    "Crowd",
    "Establishing",
]


@dataclass
class ScoreWeights:
    sharpness: float = 0.34
    exposure: float = 0.18
    contrast: float = 0.10
    composition: float = 0.10
    faces: float = 0.12
    colorfulness: float = 0.06
    stability: float = 0.10

    def normalised(self) -> dict[str, float]:
        raw = dataclasses.asdict(self)
        total = sum(raw.values()) or 1.0
        return {k: v / total for k, v in raw.items()}


@dataclass
class Config:
    # --- discovery -------------------------------------------------------
    extensions: tuple[str, ...] = VIDEO_EXTENSIONS
    min_file_bytes: int = 1_000_000          # ignore tiny proxies/thumbnails
    min_duration: float = 0.5                # seconds
    exclude_dirs: tuple[str, ...] = (
        ".Trashes", ".Spotlight-V100", "$RECYCLE.BIN", "System Volume Information",
        ".fseventsd", "__MACOSX", "PROXY", "Proxies",
    )

    # --- analysis pass ---------------------------------------------------
    analysis_width: int = 512                # decode width for scoring
    sample_fps: float = 3.0                  # candidate frames per second
    skip_head: float = 0.4                   # seconds ignored at clip start
    skip_tail: float = 0.3                   # seconds ignored at clip end
    scene_threshold: float = 0.34            # 0..1 frame-difference cut detector
    min_shot_seconds: float = 0.6

    # --- rejection gates -------------------------------------------------
    min_luma: float = 14.0                   # reject near-black frames
    max_luma: float = 243.0                  # reject blown frames
    min_contrast: float = 8.0                # std-dev of luma
    min_sharpness: float = 12.0              # raw laplacian variance floor
    max_motion: float = 46.0                 # mean abs frame delta; above = smear
    max_clipped_highlight: float = 0.16      # fraction of pixels at 255
    max_crushed_shadow: float = 0.55

    # --- selection -------------------------------------------------------
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    per_shot: int = 2                        # max stills per detected shot
    per_clip: int = 12                       # max stills per source clip
    min_score: float = 45.0                  # 0..100 composite
    min_separation: float = 1.2              # seconds between two keepers
    dedupe_distance: int = 8                 # max dHash hamming distance to call a dup
    global_limit: int = 0                    # 0 = unlimited

    # --- extraction ------------------------------------------------------
    still_format: str = "jpg"                # jpg | png | tiff
    jpeg_quality: int = 2                    # ffmpeg -q:v, 2 = visually lossless
    png_bit_depth: int = 8                   # 8 or 16
    refine: bool = True                      # micro-search for the sharpest neighbour
    refine_window: float = 0.34              # +/- seconds searched during refine
    lut: str | None = None                   # path to a .cube applied on export
    max_still_width: int = 0                 # 0 = native resolution
    thumb_width: int = 420

    # --- categorisation --------------------------------------------------
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))
    ai_model: str = "claude-opus-5"
    ai_batch_size: int = 6
    ai_thumb_width: int = 512

    # --- runtime ---------------------------------------------------------
    workers: int = 0                         # 0 = cpu_count - 1
    link_mode: str = "symlink"               # symlink | hardlink | copy

    # ---------------------------------------------------------------------
    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["extensions"] = list(self.extensions)
        data["exclude_dirs"] = list(self.exclude_dirs)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        known = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        if isinstance(kwargs.get("weights"), dict):
            kwargs["weights"] = ScoreWeights(**kwargs["weights"])
        for key in ("extensions", "exclude_dirs"):
            if key in kwargs and isinstance(kwargs[key], list):
                kwargs[key] = tuple(kwargs[key])
        return cls(**kwargs)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
