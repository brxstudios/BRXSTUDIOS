# StillHarvest

Point it at a drive of footage. It watches every clip, finds the frames that
stand on their own as photographs, exports them at full resolution, and files
them into categories.

Built for the end of a shoot: you have cards full of video, and somewhere in
there are the stills for the gallery, the pitch deck, and the client's socials.

```
stillharvest run /Volumes/SHOOT_A -o ~/Stills/ShootA
```

```
  scanned      412 files: 412 new, 0 unchanged, 0 skipped, 1.7TB / 19h12m new footage
  analysed     412 clips, 207,481 frames examined, 96,330 viable
  selected     1,204 frames (388 cross-clip duplicates dropped)
  extracted    1,204 stills
  tagged       1,204 stills categorised by rule
  organised    1,204 stills, 4,816 category links
  report       ~/Stills/ShootA/index.html
```

Open `index.html` and review the lot in one grid, filtered by category, rating,
shot size or shoot.

---

## How it decides

The work is split so that expensive things only happen to frames that have
already earned them.

**1. Scan.** Walks the drive, identifies video files, reads each clip's
resolution, frame rate, rotation, camera and capture date. Files it cannot use
are recorded with a reason rather than silently dropped — `stillharvest status`
lists them.

**2. Analyse.** Each clip is decoded *once*, at 512px and 3 frames per second,
and every sampled frame is measured:

| Measure | What it catches |
|---|---|
| Laplacian variance + Tenengrad | soft focus, motion smear |
| Histogram mean, spread, clipping | crushed blacks, blown highlights |
| Frame-to-frame delta | pans, whips, transitions |
| Gradient centroid vs. thirds | where the subject actually sits |
| Colourfulness | monochrome vs. saturated |
| Face count and size | portrait vs. landscape, and shot size |
| dHash | near-identical frames |

The same pass detects shot boundaries from tonal and spatial change, so a
20-minute interview is treated as a series of setups rather than one long take.

**3. Gate.** Frames that are too dark, blown, flat, out of focus, mid-transition
or badly clipped are rejected outright — they can never be a usable photo, and
rejecting them early means face detection (the single most expensive step) only
runs on frames still in contention.

**4. Select.** What survives is filtered down: the best few frames per shot,
spaced apart in time, deduplicated by perceptual hash within the clip and then
again across the whole drive so the same setup covered twice doesn't appear
twice.

**5. Extract.** Here the analysis timestamp is only accurate to a third of a
second, so each pick is re-decoded at native frame rate across a ±0.34s window
and moved to the genuinely sharpest frame. *Then* the full-resolution still is
written — optionally through a LUT, which is the difference between a flat log
frame and a finished photograph.

**6. Categorise and file.** Every still gets a category, shot size, people
count, lighting, colour and orientation, plus a rating relative to the rest of
the shoot. One copy lives in `stills/`; `catalog/` is links into it.

---

## Install

FFmpeg does the decoding and is the only hard requirement beyond Python 3.10+.

```bash
brew install ffmpeg                  # macOS
winget install Gyan.FFmpeg           # Windows
sudo apt install ffmpeg              # Debian/Ubuntu

pip install -e ".[all]"              # or just "." for the core
stillharvest setup                   # one-time: fetch the face model (232 KB)
```

`[all]` adds OpenCV (face detection) and the Anthropic SDK (the AI pass). Both
are optional — without them the tool still runs, it just stops distinguishing
portraits from landscapes, and `--ai` is unavailable. `stillharvest` prints
which backend is active on every run.

---

## Everyday use

```bash
# The whole thing
stillharvest run /Volumes/CARD_A -o ~/Stills/JobName

# Faster survey of a big drive, then go deeper on what looks good
stillharvest run /Volumes/ARCHIVE -o ~/Stills/Survey --preset fast
stillharvest run /Volumes/ARCHIVE -o ~/Stills/Survey --preset thorough

# Export through a LUT, as 16-bit PNG, capped at 12 per clip
stillharvest run /Volumes/CARD_A -o ~/Stills/Job \
    --lut ../LUTs/BRX_Masterclass_v2.cube --format png --per-clip 12

# Hand the folder to a client: real files, not symlinks
stillharvest organize -o ~/Stills/Job --link copy
```

Presets set sampling density and how many stills you keep:

| Preset | Sampling | Per shot | Per clip | Refine |
|---|---|---|---|---|
| `fast` | 1.5 fps @ 384px | 1 | 6 | off |
| `balanced` *(default)* | 3 fps @ 512px | 2 | 12 | on |
| `thorough` | 6 fps @ 640px | 4 | 30 | on |

### Stages run independently

`run` is just the stages in order. Each is also a command — `scan`, `analyze`,
`select`, `extract`, `tag`, `ai`, `organize`, `report` — reading and writing the
same SQLite catalog. So you can re-cut the selection without re-watching the
footage:

```bash
stillharvest select  -o ~/Stills/Job --min-score 60 --per-clip 6
stillharvest extract -o ~/Stills/Job
stillharvest report  -o ~/Stills/Job
```

### Stopping and resuming

Everything lives in `harvest.db`. Interrupt a run and start it again and it
picks up where it left off. Re-scanning a drive costs one `stat` per file:
clips already analysed, unchanged in size and mtime, are not re-probed and their
analysis is never discarded. Add more footage to the drive and only the new
material is examined. (Files that were *skipped* are always re-checked, so
relaxing `--min-file-size` re-admits them.)

---

## Categories

Every still is tagged offline, from measurements already taken:

- **Category** — Portrait, Group, Crowd, Candid, Detail, Environment, Action
- **Shot type** — Extreme Close-Up through Extreme Wide, by how much frame
  height a face fills; Detail or Environment when there is no face
- **People** — None, Solo, Duo, Small Group, Crowd
- **Lighting** — Low Key, High Key, High Contrast, Flat / Log, Balanced
- **Colour** — Warm, Cool, Neutral, Monochrome
- **Rating** — `hero` (top 12% of this shoot), `select` (next third), `usable`

### Sharper categories with Claude

Rules can tell a close-up from a wide. They cannot tell an *interview* from a
*behind-the-scenes* frame. Add `--ai` and the selected stills — thumbnails only,
in batches — go to Claude, which returns a category, a caption and keywords:

```bash
stillharvest run /Volumes/CARD_A -o ~/Stills/Job --ai
stillharvest ai -o ~/Stills/Job --categories "Interview,BTS,Product,Crowd,Landscape"
```

It prints an estimated cost and asks before spending anything (~$1.80 per 500
stills at current Opus 5 pricing). Only the stills that survived selection are
sent, never the footage. Needs `ANTHROPIC_API_KEY`, or an `ant auth login`
profile. Frames Claude flags as unusable are marked `rejected` rather than
deleted.

---

## What you get

```
~/Stills/JobName/
├── index.html            ← filterable contact sheet, opens straight from disk
├── manifest.csv          ← one row per still, for a spreadsheet or a DAM
├── manifest.json
├── harvest.db            ← the catalog; delete to start over
├── config.json           ← settings this project ran with
├── stills/<Shoot>/       ← the actual files, one copy each
├── thumbs/
└── catalog/
    ├── by-category/Portrait/…
    ├── by-shot-type/Close-Up/…
    ├── by-rating/hero/…
    └── by-shoot/<Shoot>/<Category>/…
```

Filenames sort usefully and say where they came from:

```
ShootA_A001_C0023_00-01-23-13_s087.jpg
 shoot  reel  clip   timecode   score
```

`catalog/` is symlinks by default, so a still in four categories costs one file.
`--link copy` makes real copies; `--link hardlink` sits in between. On Windows,
where symlinks need elevation, it falls back automatically.

---

## Speed

Decoding dominates — it is ~85% of the wall clock, and it scales with cores.
Measured on a modest 4-core VM at default settings:

| Workload | Throughput |
|---|---|
| One long clip (cores given to the decoder) | ~7× realtime |
| Many clips in parallel | ~5× realtime aggregate |

So roughly **12 minutes per hour of footage** on 4 cores, proportionally faster
on a real workstation. A 1 TB card of ~20 hours lands around 4 hours — run it
over lunch, or overnight for a full job. `--preset fast` trades sampling density
for a quicker first look; because the cost is decode-bound, it helps less than
you would expect, which is why `fast` also lowers the analysis resolution.

Extraction is seek-bound and much quicker: about a second per still.

---

## Limits worth knowing

- **Camera raw** — `.braw`, `.r3d`, `.ari`, `.crm` need vendor SDKs FFmpeg does
  not have. They are counted and listed by `stillharvest status`, never silently
  ignored. Transcode to ProRes/H.264 first, or use these as proxies and relink.
- **Log footage** scores low on contrast and colour by design. Either pass the
  matching `--lut`, or lower `--min-score`.
- **Face detection** is YuNet, and it is good but not infallible — profiles and
  heavy backlight get missed, which pushes a portrait into *Environment*. The
  category is a filing suggestion, not a verdict.
- **A still is not a photograph.** Rolling shutter, 180° shutter motion blur and
  8-bit 4:2:0 chroma are all still there. This finds the best frames available;
  it does not make a frame better than it was shot.

---

## Development

```bash
python3 -m unittest discover -s tests -v
```

34 tests covering the metrics, the rejection gates, selection and dedupe, the
category rules, path escaping, the catalog schema, and two end-to-end runs
against footage generated with FFmpeg (skipped automatically if FFmpeg is
absent). The AI pass is tested against a mocked client, including the
beta-unavailable fallback and a refusal.

## Layout

| Module | Responsibility |
|---|---|
| `probe.py` | walk the drive, read clip metadata |
| `analyze.py` | decode pass, shot detection, scoring, rejection gates |
| `metrics.py` | the per-frame measurements |
| `faces.py` | optional face detection and model management |
| `select.py` | quotas, spacing, perceptual dedupe |
| `extract.py` | timestamp refinement, full-res export, LUTs |
| `categorize.py` | rule tags, and the Claude vision pass |
| `organize.py` | folder trees, manifests |
| `report.py` | the HTML contact sheet |
| `pipeline.py` | stage drivers, parallelism, progress |
| `db.py` | SQLite catalog |
