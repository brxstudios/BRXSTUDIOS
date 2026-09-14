"""A self-contained HTML contact sheet for reviewing what the run pulled out.

Written to ``index.html`` in the project folder and opened straight from disk -
no server, no build step. Thumbnails are referenced by relative path, so the
whole project folder can be zipped and handed to someone else.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .organize import project_dirs

_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #14161a; --panel: #1c1f26; --line: #2c313b;
    --text: #e8eaee; --muted: #9aa3b2; --accent: #6aa9ff;
    --hero: #ffc857; --select: #6ad48a; --usable: #7f8896;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  header { position: sticky; top: 0; z-index: 10; background: var(--panel);
           border-bottom: 1px solid var(--line); padding: 14px 20px; }
  h1 { margin: 0 0 4px; font-size: 17px; letter-spacing: .2px; }
  .sub { color: var(--muted); font-size: 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
  select, input {
    background: #11131a; color: var(--text); border: 1px solid var(--line);
    border-radius: 6px; padding: 7px 9px; font-size: 13px; min-width: 0;
  }
  input[type=search] { flex: 1 1 190px; }
  input[type=range] { padding: 0; }
  .grid { display: grid; gap: 12px; padding: 18px 20px 60px;
          grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
  figure { margin: 0; background: var(--panel); border: 1px solid var(--line);
           border-radius: 9px; overflow: hidden; display: flex; flex-direction: column; }
  figure img { width: 100%; aspect-ratio: 16/9; object-fit: cover;
               display: block; background: #0b0d11; cursor: zoom-in; }
  figcaption { padding: 9px 10px 11px; font-size: 12px; }
  .row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .name { color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
  .cap { margin-top: 5px; color: #c6ccd8; }
  .tags { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 4px; }
  .tag { background: #262b35; border-radius: 4px; padding: 2px 6px;
         font-size: 10.5px; color: #b9c1cf; }
  .score { font-variant-numeric: tabular-nums; font-weight: 600; }
  .r-hero .score { color: var(--hero); }
  .r-select .score { color: var(--select); }
  .r-usable .score { color: var(--usable); }
  .r-rejected { opacity: .45; }
  .empty { padding: 40px 20px; color: var(--muted); }
  dialog { border: none; background: #0b0d11; padding: 0; max-width: 96vw; max-height: 96vh; }
  dialog img { max-width: 96vw; max-height: 86vh; display: block; }
  dialog .meta { padding: 10px 14px; color: var(--muted); font-size: 12px; }
  dialog::backdrop { background: rgba(0,0,0,.82); }
</style>
<header>
  <h1>__TITLE__</h1>
  <div class="sub">__SUBTITLE__</div>
  <div class="controls">
    <select id="f-cat"></select>
    <select id="f-rating"></select>
    <select id="f-shot"></select>
    <select id="f-shoot"></select>
    <select id="sort">
      <option value="score">Sort: score</option>
      <option value="time">Sort: clip &amp; timecode</option>
      <option value="category">Sort: category</option>
    </select>
    <label class="sub">min score <span id="minv">0</span>
      <input id="f-score" type="range" min="0" max="100" value="0"></label>
    <input id="q" type="search" placeholder="Search caption, keywords, filename&hellip;">
    <span class="sub" id="count"></span>
  </div>
</header>
<div class="grid" id="grid"></div>
<dialog id="lightbox"><img id="lb-img" alt=""><div class="meta" id="lb-meta"></div></dialog>
<script>
const DATA = __DATA__;
const $ = (id) => document.getElementById(id);
const grid = $('grid');

function fill(sel, values, label) {
  sel.innerHTML = '<option value="">' + label + ': all</option>' +
    values.map(v => '<option>' + v + '</option>').join('');
}
const uniq = (key) => [...new Set(DATA.map(d => d[key]).filter(Boolean))].sort();
fill($('f-cat'), uniq('category'), 'Category');
fill($('f-rating'), uniq('rating'), 'Rating');
fill($('f-shot'), uniq('shot_type'), 'Shot');
fill($('f-shoot'), uniq('shoot'), 'Shoot');

function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function card(d) {
  const tags = [d.shot_type, d.people, d.lighting, d.colour, d.motion, d.orientation]
    .filter(Boolean).map(t => '<span class="tag">' + esc(t) + '</span>').join('');
  return '<figure class="r-' + esc(d.rating || 'usable') + '" data-i="' + d.i + '">' +
    '<img loading="lazy" src="' + esc(d.thumb || d.path) + '" alt="' + esc(d.filename) + '">' +
    '<figcaption><div class="row"><strong>' + esc(d.category || 'Unsorted') + '</strong>' +
    '<span class="score">' + (d.score ?? 0).toFixed(0) + '</span></div>' +
    (d.caption ? '<div class="cap">' + esc(d.caption) + '</div>' : '') +
    '<div class="tags">' + tags + '</div>' +
    '<div class="name">' + esc(d.clip_name) + ' @ ' + esc(d.timecode) + '</div>' +
    '</figcaption></figure>';
}

function render() {
  const cat = $('f-cat').value, rating = $('f-rating').value;
  const shot = $('f-shot').value, shoot = $('f-shoot').value;
  const minScore = +$('f-score').value;
  const q = $('q').value.trim().toLowerCase();
  $('minv').textContent = minScore;

  let rows = DATA.filter(d =>
    (!cat || d.category === cat) && (!rating || d.rating === rating) &&
    (!shot || d.shot_type === shot) && (!shoot || d.shoot === shoot) &&
    (d.score ?? 0) >= minScore &&
    (!q || (d.search || '').includes(q)));

  const sort = $('sort').value;
  rows = rows.slice().sort((a, b) =>
    sort === 'time' ? (a.clip_name + a.t).localeCompare(b.clip_name + b.t)
    : sort === 'category' ? String(a.category).localeCompare(String(b.category)) || b.score - a.score
    : b.score - a.score);

  $('count').textContent = rows.length + ' of ' + DATA.length + ' stills';
  grid.innerHTML = rows.length ? rows.map(card).join('')
    : '<div class="empty">Nothing matches these filters.</div>';
}

grid.addEventListener('click', (e) => {
  const fig = e.target.closest('figure');
  if (!fig) return;
  const d = DATA[+fig.dataset.i];
  $('lb-img').src = d.path;
  $('lb-meta').textContent =
    [d.filename, d.clip_name + ' @ ' + d.timecode, d.category,
     'score ' + (d.score ?? 0).toFixed(1), d.caption, d.keywords]
    .filter(Boolean).join('  -  ');
  $('lightbox').showModal();
});
$('lightbox').addEventListener('click', () => $('lightbox').close());

['f-cat','f-rating','f-shot','f-shoot','sort','f-score','q']
  .forEach(id => $(id).addEventListener('input', render));
render();
</script>
"""


def _relative(target: str | None, root: Path) -> str | None:
    if not target:
        return None
    try:
        return os.path.relpath(Path(target), root).replace(os.sep, "/")
    except ValueError:            # different drive on Windows
        return Path(target).as_uri()


def build_report(conn: sqlite3.Connection, out_dir: str | Path, *, title: str | None = None) -> Path:
    dirs = project_dirs(out_dir)
    root = dirs["root"]
    rows = list(conn.execute(
        "SELECT s.*, c.shoot AS shoot, c.reel AS reel, c.path AS clip_path "
        "FROM stills s JOIN clips c ON c.id = s.clip_id ORDER BY s.score DESC"
    ))

    payload: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        category = row["ai_category"] or row["category"] or "Unsorted"
        searchable = " ".join(str(x).lower() for x in (
            row["filename"], row["ai_caption"], row["ai_keywords"],
            category, row["shot_type"], row["shoot"], Path(row["clip_path"]).name,
        ) if x)
        payload.append({
            "i": index,
            "filename": row["filename"],
            "path": _relative(row["path"], root),
            "thumb": _relative(row["thumb"], root),
            "clip_name": Path(row["clip_path"]).name,
            "shoot": row["shoot"],
            "timecode": row["timecode"],
            "t": f"{float(row['t'] or 0):09.3f}",
            "score": round(float(row["score"] or 0.0), 1),
            "rating": row["rating"] or "usable",
            "category": category,
            "shot_type": row["shot_type"],
            "people": row["people"],
            "lighting": row["lighting"],
            "colour": row["colour"],
            "motion": row["motion"],
            "orientation": row["orientation"],
            "caption": row["ai_caption"],
            "keywords": row["ai_keywords"],
            "search": searchable,
        })

    shoots = sorted({str(r["shoot"]) for r in rows if r["shoot"]})
    subtitle = (
        f"{len(payload)} stills"
        + (f" from {len(shoots)} shoot{'s' if len(shoots) != 1 else ''}" if shoots else "")
        + " - click any frame for full resolution"
    )
    html = (
        _TEMPLATE
        .replace("__TITLE__", _escape(title or (root.name or "StillHarvest")))
        .replace("__SUBTITLE__", _escape(subtitle))
        .replace("__DATA__", json.dumps(payload).replace("</", "<\\/"))
    )
    dirs["report"].write_text(html, encoding="utf-8")
    return dirs["report"]


def _escape(text: str) -> str:
    return (
        str(text).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )
