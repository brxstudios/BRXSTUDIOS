"""Command line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import db as dbm
from . import faces, organize, pipeline, report
from .config import Config
from .extract import validate_lut
from .util import ToolMissing, human_duration, human_size, parse_size, require_tools

log = logging.getLogger("stillharvest")

STAGES = ("scan", "analyze", "select", "extract", "tag", "organize", "report")

PRESETS = {
    "fast":     dict(sample_fps=1.5, analysis_width=384, per_shot=1, per_clip=6, refine=False),
    "balanced": dict(sample_fps=3.0, analysis_width=512, per_shot=2, per_clip=12, refine=True),
    "thorough": dict(sample_fps=6.0, analysis_width=640, per_shot=4, per_clip=30, refine=True),
}


# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stillharvest",
        description="Review every frame of footage on a drive and pull out the "
                    "frames worth keeping as photographs, filed by category.",
    )
    # Shared flags are attached to every subcommand as well as the top level,
    # so `stillharvest run DRIVE -o OUT --quiet` works as naturally as
    # `stillharvest --quiet run DRIVE -o OUT`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    common.add_argument("--quiet", "-q", action="store_true", help="no progress bar")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="no progress bar")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("-o", "--out", required=True, metavar="DIR",
                       help="project folder holding the catalog and output")

    def add_tuning(p: argparse.ArgumentParser) -> None:
        p.add_argument("--preset", choices=sorted(PRESETS), help="speed/thoroughness tradeoff")
        p.add_argument("--workers", type=int, help="parallel processes (default: cores - 1)")
        p.add_argument("--sample-fps", type=float, help="frames examined per second of footage")
        p.add_argument("--per-shot", type=int, help="max stills kept per detected shot")
        p.add_argument("--per-clip", type=int, help="max stills kept per source clip")
        p.add_argument("--min-score", type=float, help="0-100 quality floor")
        p.add_argument("--limit", type=int, dest="global_limit",
                       help="hard cap on total stills (0 = no cap)")
        p.add_argument("--format", dest="still_format", choices=["jpg", "png", "tiff"],
                       help="still format (default jpg)")
        p.add_argument("--lut", help="path to a .cube LUT applied on export")
        p.add_argument("--max-width", type=int, dest="max_still_width",
                       help="downscale exported stills to this width")
        p.add_argument("--link", dest="link_mode", choices=["symlink", "hardlink", "copy"],
                       help="how the category folders reference the stills")
        p.add_argument("--min-file-size", dest="min_file_bytes", type=parse_size,
                       metavar="SIZE",
                       help="ignore files smaller than this (default 1MB; "
                            "accepts 800k, 1.5MB)")
        p.add_argument("--min-duration", type=float, metavar="SECONDS",
                       help="ignore clips shorter than this (default 0.5)")
        p.add_argument("--no-faces", action="store_true",
                       help="skip face detection even if a model is present")

    run = sub.add_parser("run", parents=[common], help="scan, analyse, extract, categorise and report")
    run.add_argument("drive", help="folder or mounted drive holding the footage")
    add_project(run); add_tuning(run)
    run.add_argument("--ai", action="store_true", help="also classify stills with Claude")
    run.add_argument("--ai-limit", type=int, default=0, help="cap how many stills go to the API")
    run.add_argument("--yes", action="store_true", help="skip the AI cost confirmation")
    run.add_argument("--rescan", action="store_true",
                     help="re-probe files already in the catalog (discards their analysis)")

    scan = sub.add_parser("scan", parents=[common], help="index the footage on a drive")
    scan.add_argument("drive"); add_project(scan); add_tuning(scan)
    scan.add_argument("--rescan", action="store_true",
                      help="re-probe files already in the catalog (discards their analysis)")

    for name, help_text in (
        ("analyze", "measure sampled frames of indexed clips"),
        ("select", "choose which frames to extract"),
        ("extract", "export full-resolution stills"),
        ("tag", "apply offline rule-based categories"),
        ("organize", "rebuild category folders and manifests"),
        ("report", "rebuild the HTML contact sheet"),
    ):
        p = sub.add_parser(name, parents=[common], help=help_text)
        add_project(p); add_tuning(p)
        if name == "analyze":
            p.add_argument("--reanalyze", action="store_true", help="re-measure analysed clips")

    ai = sub.add_parser("ai", parents=[common], help="classify extracted stills with Claude vision")
    add_project(ai); add_tuning(ai)
    ai.add_argument("--ai-limit", type=int, default=0, help="cap how many stills go to the API")
    ai.add_argument("--model", help="Claude model id (default claude-opus-5)")
    ai.add_argument("--categories", help="comma-separated category list to choose from")
    ai.add_argument("--yes", action="store_true", help="skip the cost confirmation")

    status = sub.add_parser("status", parents=[common], help="show what is in the catalog")
    add_project(status)

    sub.add_parser("setup", parents=[common], help="download the face-detection model")
    return parser


# --------------------------------------------------------------------------

def resolve_config(args: argparse.Namespace, out_dir: Path) -> Config:
    """Project config, then preset, then explicit flags."""
    config_path = organize.project_dirs(out_dir)["config"]
    cfg = Config.load(config_path) if config_path.is_file() else Config()

    for key, value in PRESETS.get(getattr(args, "preset", None) or "", {}).items():
        setattr(cfg, key, value)

    simple = (
        "workers", "sample_fps", "per_shot", "per_clip", "min_score", "global_limit",
        "still_format", "lut", "max_still_width", "link_mode",
        "min_file_bytes", "min_duration",
    )
    for key in simple:
        value = getattr(args, key, None)
        if value is not None:
            setattr(cfg, key, value)

    if getattr(args, "model", None):
        cfg.ai_model = args.model
    if getattr(args, "categories", None):
        cfg.categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if getattr(args, "no_faces", False):
        cfg.weights.faces = 0.0
    if cfg.lut:
        validate_lut(cfg.lut)
    return cfg


def confirm_ai(count: int, cfg: Config, assume_yes: bool) -> bool:
    estimate = pipeline.cat.estimate_cost(count, cfg)
    print(f"  AI pass: {count} stills -> {cfg.ai_model}, estimated ~${estimate:.2f}")
    if assume_yes or not sys.stdin.isatty():
        return True
    return input("  Continue? [y/N] ").strip().lower() in ("y", "yes")


def _print(label: str, detail: str) -> None:
    print(f"  {label:<12} {detail}")


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "setup":
        try:
            path = faces.download_model()
        except Exception as exc:
            print(f"Could not download the face model: {exc}", file=sys.stderr)
            return 1
        faces._backend.cache_clear()
        print(f"Face model ready: {path}\n{faces.status()}")
        return 0

    try:
        require_tools("ffmpeg", "ffprobe")
    except ToolMissing as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out_dir = Path(args.out).expanduser().resolve()
    dirs = organize.ensure_dirs(out_dir)
    conn = dbm.connect(dirs["db"])

    try:
        cfg = resolve_config(args, out_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Configuration problem: {exc}", file=sys.stderr)
        return 1
    cfg.save(dirs["config"])

    quiet = args.quiet
    command = args.command

    if command == "status":
        return _status(conn, out_dir)

    print(f"StillHarvest -> {out_dir}")
    print(f"  {faces.status()}")

    if command in ("run", "scan"):
        drive = Path(args.drive).expanduser().resolve()
        if not drive.is_dir():
            print(f"Not a folder: {drive}", file=sys.stderr)
            return 1
        result = pipeline.stage_scan(
            conn, drive, cfg, quiet=quiet, rescan=getattr(args, "rescan", False)
        )
        _print("scanned", (
            f"{result['found']} files: {result['usable']} new, "
            f"{result['unchanged']} unchanged, {result['skipped']} skipped, "
            f"{human_size(result['bytes'])} / {human_duration(result['seconds'])} new footage"
        ))
        if result["unsupported"]:
            _print("note", f"{result['unsupported']} camera-raw files FFmpeg cannot read "
                           "(see `stillharvest status`)")
        if command == "scan":
            return 0

    if command in ("run", "analyze"):
        result = pipeline.stage_analyze(
            conn, cfg, workers=cfg.workers,
            reanalyze=getattr(args, "reanalyze", False), quiet=quiet,
        )
        _print("analysed", f"{result['clips']} clips, {result['frames']} frames examined, "
                           f"{result['candidates']} viable")
        if command == "analyze":
            return 0

    if command in ("run", "select"):
        result = pipeline.stage_select(conn, cfg)
        _print("selected", f"{result['selected']} frames "
                           f"({result['dropped_cross_clip']} cross-clip duplicates dropped)")
        if command == "select":
            return 0

    if command in ("run", "extract"):
        result = pipeline.stage_extract(conn, cfg, out_dir, workers=cfg.workers, quiet=quiet)
        _print("extracted", f"{result['extracted']} stills"
                            + (f", {result['failed']} failed" if result["failed"] else ""))
        if command == "extract":
            return 0

    if command in ("run", "tag"):
        result = pipeline.stage_tag(conn)
        _print("tagged", f"{result['tagged']} stills categorised by rule")
        if command == "tag":
            return 0

    if command == "ai" or (command == "run" and getattr(args, "ai", False)):
        pending = conn.execute(
            "SELECT COUNT(*) FROM stills WHERE ai_category IS NULL"
        ).fetchone()[0]
        limit = getattr(args, "ai_limit", 0) or 0
        count = min(pending, limit) if limit > 0 else pending
        if count == 0:
            _print("ai", "nothing left to classify")
        elif confirm_ai(count, cfg, getattr(args, "yes", False)):
            try:
                result = pipeline.stage_ai(conn, cfg, limit=limit, quiet=quiet)
                _print("ai", f"{result['classified']} stills classified "
                             f"(~${result['cost_estimate']:.2f})")
            except RuntimeError as exc:
                print(f"  AI pass unavailable: {exc}", file=sys.stderr)
        else:
            _print("ai", "skipped")
        if command == "ai":
            command = "organize"      # keep the catalog consistent afterwards

    if command in ("run", "organize", "ai"):
        result = organize.build_catalog(conn, out_dir, cfg.link_mode)
        manifests = organize.write_manifests(conn, out_dir)
        _print("organised", f"{result['stills']} stills, {result['links']} category links")
        _print("manifest", manifests["csv"])
        if command == "organize":
            command = "report"

    if command in ("run", "report", "ai"):
        path = report.build_report(conn, out_dir, title=out_dir.name)
        _print("report", str(path))

    summary = organize.category_summary(conn)
    if summary:
        print("\n  Categories")
        for name, number in summary:
            print(f"    {name:<22} {number}")
    conn.close()
    return 0


def _status(conn, out_dir: Path) -> int:
    stats = dbm.counts(conn)
    print(f"StillHarvest project: {out_dir}")
    for key, value in stats.items():
        _print(key, str(value))
    unsupported = dbm.get_meta(conn, "unsupported", [])
    if unsupported:
        print(f"\n  {len(unsupported)} camera-raw file(s) FFmpeg cannot decode:")
        for path in unsupported[:10]:
            print(f"    {path}")
        if len(unsupported) > 10:
            print(f"    ... and {len(unsupported) - 10} more")
    problems = list(conn.execute(
        "SELECT path, note FROM clips WHERE status IN ('skipped','error') AND note IS NOT NULL LIMIT 10"
    ))
    if problems:
        print("\n  Skipped clips:")
        for row in problems:
            print(f"    {Path(row['path']).name}: {row['note']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
