"""Test suite. The end-to-end cases need ffmpeg and are skipped without it."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stillharvest import categorize as cat
from stillharvest import db as dbm
from stillharvest import organize, select
from stillharvest.analyze import (analysis_dimensions, composite_score,
                                  rejection_reason, scene_distance, _histogram)
from stillharvest.config import Config
from stillharvest.extract import build_chain, escape_filter_path, still_filename
from stillharvest.metrics import (dhash, hamming, laplacian_variance, luma,
                                  measure, phash_from_hex, phash_to_hex)
from stillharvest.util import parse_size, slugify, timecode

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def noise(h=180, w=320, seed=0):
    return (np.random.default_rng(seed).random((h, w, 3)) * 255).astype(np.uint8)


def blurred(img, factor=8):
    small = img[::factor, ::factor]
    return np.repeat(np.repeat(small, factor, 0), factor, 1)[: img.shape[0], : img.shape[1]]


class TestMetrics(unittest.TestCase):
    def test_sharp_beats_blurred(self):
        sharp, soft = noise(), blurred(noise())
        self.assertGreater(laplacian_variance(luma(sharp)), 10 * laplacian_variance(luma(soft)))

    def test_phash_roundtrip_handles_top_bit(self):
        for value in (0, 1, 2 ** 63, 2 ** 64 - 1):
            self.assertEqual(phash_from_hex(phash_to_hex(value)), value)
        self.assertIsNone(phash_to_hex(None))
        self.assertIsNone(phash_from_hex(None))
        self.assertIsNone(phash_from_hex("not-hex"))

    def test_identical_frames_hash_identically(self):
        img = noise()
        self.assertEqual(hamming(dhash(luma(img)), dhash(luma(img.copy()))), 0)

    def test_measure_reports_expected_keys(self):
        m = measure(noise(), None, want_faces=False)
        for key in ("lap_var", "mean", "std", "motion", "phash", "composition", "face_count"):
            self.assertIn(key, m)


class TestGates(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()

    def _metrics(self, **overrides):
        base = dict(mean=120.0, std=40.0, lap_var=500.0, motion=2.0,
                    clipped_high=0.0, crushed_low=0.0)
        base.update(overrides)
        return base

    def test_good_frame_passes(self):
        self.assertIsNone(rejection_reason(self._metrics(), self.cfg))

    def test_each_gate_fires(self):
        cases = {
            "too dark": dict(mean=5.0),
            "blown out": dict(mean=250.0),
            "flat/blank frame": dict(std=2.0),
            "out of focus": dict(lap_var=1.0),
            "motion smear / transition": dict(motion=90.0),
            "clipped highlights": dict(clipped_high=0.5),
            "crushed shadows": dict(crushed_low=0.9),
        }
        for expected, overrides in cases.items():
            with self.subTest(expected):
                self.assertEqual(rejection_reason(self._metrics(**overrides), self.cfg), expected)

    def test_score_is_bounded_and_ordered(self):
        cfg = Config()
        good = measure(noise(), None, want_faces=False)
        poor = measure(blurred(noise()), None, want_faces=False)
        good_score = composite_score(good, cfg, False)
        poor_score = composite_score(poor, cfg, False)
        self.assertTrue(0 <= poor_score <= good_score <= 100)


class TestSceneDetection(unittest.TestCase):
    def test_cut_scores_higher_than_continuity(self):
        a, b = luma(noise(seed=1)), luma(noise(seed=2))
        same = luma(noise(seed=1))
        cut = scene_distance(b, a, _histogram(b), _histogram(a))
        cont = scene_distance(same, a, _histogram(same), _histogram(a))
        self.assertGreater(cut, cont)
        self.assertAlmostEqual(cont, 0.0, places=6)


class TestSelection(unittest.TestCase):
    def test_dedupe_keeps_highest_scorer(self):
        rows = [
            {"id": 1, "score": 50.0, "phash": 0b1010, "t": 0.0},
            {"id": 2, "score": 90.0, "phash": 0b1011, "t": 1.0},   # near-duplicate of 1
            {"id": 3, "score": 70.0, "phash": (1 << 63) | 0xFF, "t": 2.0},
        ]
        kept = {r["id"] for r in select._dedupe(rows, distance=2)}
        self.assertEqual(kept, {2, 3})

    def test_spacing_is_enforced(self):
        rows = [{"id": i, "score": 100 - i, "t": i * 0.2} for i in range(10)]
        picked = select._spaced(rows, limit=3, min_gap=1.0)
        times = sorted(r["t"] for r in picked)
        self.assertTrue(all(b - a >= 1.0 for a, b in zip(times, times[1:])))


class TestCategories(unittest.TestCase):
    def test_shot_type_tracks_face_size(self):
        sizes = [(0.7, "Extreme Close-Up"), (0.4, "Close-Up"), (0.2, "Medium Close-Up"),
                 (0.1, "Medium"), (0.05, "Wide"), (0.01, "Extreme Wide")]
        for frac, expected in sizes:
            with self.subTest(frac=frac):
                self.assertEqual(
                    cat.shot_type({"face_count": 1, "face_height_frac": frac}), expected
                )

    def test_faceless_frames_split_by_detail(self):
        self.assertEqual(cat.shot_type({"face_count": 0, "edge_density": 0.4}), "Detail")
        self.assertEqual(cat.shot_type({"face_count": 0, "edge_density": 0.01}), "Environment")

    def test_people_buckets(self):
        for count, expected in ((0, "None"), (1, "Solo"), (2, "Duo"), (4, "Small Group"), (9, "Crowd")):
            self.assertEqual(cat.people({"face_count": count}), expected)

    def test_ratings_are_ranked(self):
        ratings = cat.rank_ratings([100, 90, 80, 70, 60, 50, 40, 30, 20, 10])
        self.assertEqual(ratings[0], "hero")
        self.assertEqual(ratings[-1], "usable")
        self.assertEqual(len(ratings), 10)

    def test_orientation(self):
        self.assertEqual(cat.orientation(1920, 1080), "Landscape")
        self.assertEqual(cat.orientation(1080, 1920), "Portrait")
        self.assertEqual(cat.orientation(1000, 1000), "Square")

    def test_normalise_snaps_category_and_clamps_quality(self):
        out = cat.normalise_entry(
            {"category": "portrait", "caption": " A person ", "keywords": ["Face", " Studio "],
             "quality": 5.0, "usable": True},
            Config().categories,
        )
        self.assertEqual(out["ai_category"], "Portrait")
        self.assertEqual(out["ai_caption"], "A person")
        self.assertEqual(out["ai_keywords"], "face, studio")
        self.assertEqual(out["ai_quality"], 1.0)

    def test_unknown_category_is_preserved_not_dropped(self):
        out = cat.normalise_entry({"category": "Pyrotechnics", "quality": 0.5}, ["Portrait"])
        self.assertEqual(out["ai_category"], "Pyrotechnics")


class TestAIRequest(unittest.TestCase):
    def test_batch_message_pairs_labels_and_images(self):
        content = cat.build_batch_message([b"a", b"b"], ["Portrait", "Detail"])[0]["content"]
        self.assertEqual(sum(1 for b in content if b["type"] == "image"), 2)
        self.assertIn("Portrait", content[0]["text"])
        self.assertEqual(content[1]["text"], "Image 1:")
        self.assertEqual(content[3]["text"], "Image 2:")

    def test_classify_falls_back_when_beta_unavailable(self):
        payload = {"entries": [{"category": "Detail", "caption": "c", "keywords": [],
                                "quality": 0.5, "usable": True}]}
        calls = []

        class StableMessages:
            def create(self, **kwargs):
                calls.append("stable")
                return types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(type="text", text=json.dumps(payload))],
                )

        class BetaMessages:
            def create(self, **kwargs):
                calls.append("beta")
                raise TypeError("unexpected keyword argument 'fallbacks'")

        client = types.SimpleNamespace(
            messages=StableMessages(), beta=types.SimpleNamespace(messages=BetaMessages())
        )
        entries = cat.classify_batch(client, [b"img"], Config())
        self.assertEqual(calls, ["beta", "stable"])
        self.assertEqual(entries[0]["category"], "Detail")

    def test_refusal_returns_no_entries(self):
        class Messages:
            def create(self, **kwargs):
                return types.SimpleNamespace(stop_reason="refusal", content=[])

        client = types.SimpleNamespace(
            messages=Messages(), beta=types.SimpleNamespace(messages=Messages())
        )
        self.assertEqual(cat.classify_batch(client, [b"x"], Config()), [])

    def test_cost_estimate_scales(self):
        cfg = Config()
        self.assertGreater(cat.estimate_cost(1000, cfg), cat.estimate_cost(100, cfg))


class TestPaths(unittest.TestCase):
    def test_windows_drive_is_escaped_for_filtergraph(self):
        self.assertEqual(escape_filter_path(r"C:\LUTs\a.cube"), "C\\:/LUTs/a.cube")

    def test_lut_chain_uses_the_file_option(self):
        chain = build_chain(Config(lut="/x/y.cube"))
        self.assertIn("lut3d=file=/x/y.cube", chain)

    def test_filename_is_sortable_and_safe(self):
        name = still_filename(
            {"path": "/v/C0023.MOV", "shoot": "Main Shoot!", "reel": "A001", "fps": 25.0},
            83.5, 87.4, ".jpg",
        )
        self.assertEqual(name, "Main-Shoot_A001_C0023_00-01-23-13_s087.jpg")

    def test_helpers(self):
        self.assertEqual(timecode(0, 25), "00-00-00-00")
        self.assertEqual(slugify("A / B"), "A-B")
        self.assertEqual(parse_size("1.5MB"), 1572864)

    def test_analysis_caps_the_long_edge(self):
        self.assertEqual(analysis_dimensions(3840, 2160, 0, 512), (512, 288))
        self.assertEqual(analysis_dimensions(1080, 1920, 0, 512), (288, 512))
        self.assertEqual(analysis_dimensions(1920, 1080, 90, 512), (288, 512))


class TestOrganize(unittest.TestCase):
    def test_placement_modes_all_produce_a_readable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src" / "a.jpg"
            src.parent.mkdir()
            src.write_bytes(b"data")
            for mode in ("symlink", "hardlink", "copy"):
                dst = root / mode / "a.jpg"
                self.assertTrue(organize.place(src, dst, mode))
                self.assertEqual(dst.read_bytes(), b"data")

    def test_bucket_falls_back(self):
        self.assertEqual(organize._bucket(None), "Unsorted")
        self.assertEqual(organize._bucket("  "), "Unsorted")
        self.assertEqual(organize._bucket(None, "usable"), "usable")


class TestDatabase(unittest.TestCase):
    def test_frames_store_full_range_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = dbm.connect(Path(tmp) / "t.db")
            clip_id = dbm.upsert_clip(conn, {"path": "/a.mov", "duration": 1.0, "status": "new"})
            dbm.replace_frames(conn, clip_id, [
                {"t": 0.0, "shot": 0, "score": 50.0, "phash": 2 ** 64 - 1,
                 "metrics": {}, "rejected": None}
            ])
            conn.commit()
            row = conn.execute("SELECT phash FROM frames").fetchone()
            self.assertEqual(phash_from_hex(row["phash"]), 2 ** 64 - 1)

    def test_upsert_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = dbm.connect(Path(tmp) / "t.db")
            first = dbm.upsert_clip(conn, {"path": "/a.mov", "duration": 1.0, "status": "new"})
            second = dbm.upsert_clip(conn, {"path": "/a.mov", "duration": 2.0, "status": "analyzed"})
            self.assertEqual(first, second)
            self.assertEqual(dbm.counts(conn)["clips"], 1)


class TestConfig(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            cfg = Config(per_clip=7, still_format="png")
            cfg.weights.faces = 0.0
            cfg.save(path)
            loaded = Config.load(path)
            self.assertEqual(loaded.per_clip, 7)
            self.assertEqual(loaded.still_format, "png")
            self.assertEqual(loaded.weights.faces, 0.0)

    def test_weights_normalise_to_one(self):
        self.assertAlmostEqual(sum(Config().weights.normalised().values()), 1.0)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg is required")
class TestEndToEnd(unittest.TestCase):
    """Generate footage, run the whole pipeline, and check the artefacts."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.drive = Path(cls.tmp) / "drive" / "ShootX" / "A001"
        cls.drive.mkdir(parents=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=2",
             "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=2",
             "-filter_complex", "[1:v]gblur=sigma=16[b];[0:v][b]concat=n=2:v=1:a=0[v]",
             "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
             "-pix_fmt", "yuv420p", str(cls.drive / "clip.mov")],
            check=True, stdin=subprocess.DEVNULL,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_run_produces_stills_manifest_and_report(self):
        from stillharvest.cli import main

        out = Path(self.tmp) / "project"
        code = main([
            "run", str(Path(self.tmp) / "drive"), "-o", str(out),
            "--min-file-size", "1k", "--quiet", "--per-clip", "3",
        ])
        self.assertEqual(code, 0)

        stills = list((out / "stills").rglob("*.jpg"))
        self.assertTrue(stills, "expected at least one extracted still")
        self.assertTrue((out / "manifest.csv").is_file())
        self.assertTrue((out / "index.html").is_file())
        self.assertTrue(list((out / "catalog").rglob("*.jpg")))

        data = json.loads((out / "manifest.json").read_text())
        self.assertEqual(data["count"], len(stills))
        for row in data["stills"]:
            self.assertTrue(Path(row["path"]).is_file())
            self.assertIn(row["rating"], ("hero", "select", "usable"))

        html = (out / "index.html").read_text()
        self.assertIn("const DATA =", html)

    def test_rerun_is_incremental(self):
        from stillharvest.cli import main

        out = Path(self.tmp) / "project2"
        args = ["run", str(Path(self.tmp) / "drive"), "-o", str(out),
                "--min-file-size", "1k", "--quiet"]
        self.assertEqual(main(args), 0)
        before = sorted(p.name for p in (out / "stills").rglob("*.jpg"))
        self.assertEqual(main(args), 0)
        after = sorted(p.name for p in (out / "stills").rglob("*.jpg"))
        self.assertEqual(before, after, "a second run must not duplicate stills")


if __name__ == "__main__":
    unittest.main(verbosity=2)
