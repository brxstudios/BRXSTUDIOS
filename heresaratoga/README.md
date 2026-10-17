# HereSaratoga.com

The complete guide to Saratoga Springs, NY: events calendar, guides and a directory of places to eat, drink, stay and explore.

Built with [Astro](https://astro.build). Static site, no database, fast and cheap to host.

## Run it

```bash
cd heresaratoga
npm install
npm run dev        # http://localhost:4321
npm run build      # production build in dist/
```

## Where things live

| What | File |
|---|---|
| Guides (articles) | `src/content/guides/*.md` |
| Events calendar | `src/data/events.json` |
| Directory (eat, drink, stay, see, do, shop) | `src/data/places.json` |
| Navigation, directory sections, site name | `src/data/site.ts` |
| Colors & type (cobalt `#0047AB`) | `src/styles/global.css` |
| Photos | `public/images/` (find licensed ones with `npm run find-image`) |

Writing, photo and fact-checking rules: **[CONTENT_GUIDE.md](CONTENT_GUIDE.md)**.

## Forms

Copy `.env.example` to `.env` and set:

- `PUBLIC_EVENT_FORM_ENDPOINT`: a Formspree (or similar) URL for event submissions.
- `PUBLIC_NEWSLETTER_ENDPOINT`: your newsletter provider's form endpoint (beehiiv recommended).

Left blank, both fall back to emailing `PUBLIC_CONTACT_EMAIL`.

## Deploy to HereSaratoga.com

1. Push this repo to GitHub.
2. In Netlify or Vercel, import the repo. Set **root directory** `heresaratoga`, build command `npm run build`, output `dist`.
3. Add the env vars above.
4. Add `heresaratoga.com` as a custom domain and update DNS at your registrar as instructed.
5. **Schedule a daily rebuild** (Netlify build hook or Vercel deploy hook, triggered by a free cron service or a GitHub Action) so past events drop off the calendar.
