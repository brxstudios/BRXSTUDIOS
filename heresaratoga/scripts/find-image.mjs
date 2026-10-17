#!/usr/bin/env node
// Find freely licensed photos on Wikimedia Commons and download one with its credit.
//
//   npm run find-image -- "Congress Park Saratoga"            # list candidates
//   npm run find-image -- "Congress Park Saratoga" 2 congress-park   # download #2 as public/images/congress-park.jpg
//
// Prints an `image:` block to paste into a guide's frontmatter or places.json.
import { writeFile, mkdir } from 'node:fs/promises';

const [query, pick, slug] = process.argv.slice(2);
if (!query) {
  console.error('Usage: npm run find-image -- "<search>" [number] [slug]');
  process.exit(1);
}

const UA = 'HereSaratoga/0.1 (https://heresaratoga.com)';
// Licenses that allow commercial use with attribution.
const OK = /^(CC0|CC BY(-SA)? [\d.]+|Public domain|PD)/i;

const api = new URL('https://commons.wikimedia.org/w/api.php');
Object.entries({
  action: 'query', format: 'json', generator: 'search', gsrnamespace: '6',
  gsrsearch: `${query} filetype:bitmap`, gsrlimit: '20',
  prop: 'imageinfo', iiprop: 'url|extmetadata|size', iiurlwidth: '1600',
}).forEach(([k, v]) => api.searchParams.set(k, v));

const res = await fetch(api, { headers: { 'User-Agent': UA } });
const pages = Object.values((await res.json()).query?.pages ?? {}).sort((a, b) => a.index - b.index);

const strip = (html = '') => html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const results = pages
  .map((p) => {
    const ii = p.imageinfo?.[0];
    const m = ii?.extmetadata ?? {};
    return {
      title: p.title.replace(/^File:/, ''),
      thumb: ii?.thumburl,
      size: `${ii?.width}x${ii?.height}`,
      credit: strip(m.Artist?.value) || 'Unknown',
      license: strip(m.LicenseShortName?.value),
      sourceUrl: ii?.descriptionurl,
      alt: strip(m.ImageDescription?.value).slice(0, 140),
    };
  })
  .filter((r) => r.thumb && OK.test(r.license));

if (!results.length) {
  console.log('No commercially usable results. Try a different search.');
  process.exit(0);
}

if (!pick) {
  results.forEach((r, i) => console.log(`${i + 1}. ${r.title}\n   ${r.size} · ${r.license} · ${r.credit}\n   ${r.sourceUrl}\n`));
  console.log('Open the links, pick one, then rerun with its number and a slug.');
  process.exit(0);
}

const r = results[Number(pick) - 1];
if (!r || !slug) {
  console.error('Give a valid number and a slug, e.g. 2 congress-park');
  process.exit(1);
}
const img = await fetch(r.thumb, { headers: { 'User-Agent': UA } });
await mkdir('public/images', { recursive: true });
await writeFile(`public/images/${slug}.jpg`, Buffer.from(await img.arrayBuffer()));

console.log(`Saved public/images/${slug}.jpg\n\nFrontmatter (guides):\nimage:
  src: "/images/${slug}.jpg"
  alt: "${(r.alt || r.title).replace(/"/g, "'")}"
  credit: "${r.credit.replace(/"/g, "'")}"
  license: "${r.license}"
  sourceUrl: "${r.sourceUrl}"

JSON (places.json):
${JSON.stringify({ image: { src: `/images/${slug}.jpg`, alt: r.alt || r.title, credit: r.credit, license: r.license, sourceUrl: r.sourceUrl } }, null, 2)}

Check the alt text describes the photo, and note any "modified" credit if you crop or edit it.`);
