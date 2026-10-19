# HereSaratoga: project handoff

Read this first. It covers everything decided and built so far, in an earlier cloud session (Oct 17–19, 2026), so a new session can pick up where that one left off.

## The project

- **Owner:** Joshua. Personal project, separate from BRX Studios client work.
- **Domain:** HereSaratoga.com (already owned, not live).
- **Goal:** replicate **There San Diego** (theresandiego.com) for **Saratoga Springs, NY**. It's a complete local guide (food, events, things to do, travel), set up as a local media business that earns from sponsored stories, newsletter ads and Instagram promotion.
- **Brand color:** cobalt blue `#0047AB`.
- **Content:** written by AI and fact-checked by a person. Photos must come from licensed sources: Wikimedia Commons, Unsplash/Pexels, the business's own photos or press shots. Never Google Images or Instagram.
- **Phase:** PLANNING. Joshua is building this over the next few weeks. **Nothing goes live and nothing gets deployed** unless he asks.
- The user dropped "event space" (hosting their own events or a venue). It's a guide, like There San Diego.

## Immediate next step (why this session exists)

The cloud session couldn't open theresandiego.com: the network policy blocked it, and the WebFetch tool's DNS lookups failed. So the review in `../reports/There San Diego site review.md` is built **only from search-engine indexes**. With a local browser (Claude in Chrome or the Desktop browser pane):

1. Open https://theresandiego.com and walk through it. Record the header nav, homepage sections in order, footer, The Craving page, the weekend Big List, a "Best Restaurants Right Now" guide, an event page, /advertise, /packages, and offers.theresandiego.com pages (SponsoredStories-page, newsletter-ads-page).
2. Take screenshots. Note the visual style (colors, fonts, layout, photos) and how sponsored posts are labeled.
3. Check their Instagram @theresandiego: post types, reels vs. static posts, giveaways.
4. Correct the report anywhere the search-based findings were wrong. In particular, re-check prices, subscriber counts, newsletter days and the homepage layout.
5. Then revise the HereSaratoga concept design to match the real site.

## What exists

| Thing | Where | Status |
|---|---|---|
| Full review of There San Diego plus a plan for Saratoga | `../reports/There San Diego site review.md` | Done, from search data only. Needs checking against the live site. |
| Research notes behind it (4 files) | `../research_notes/There San Diego site review/` | Done |
| Concept design (3 artboards: homepage, brand board, phone guide page) | Canvas: https://claude.ai/artifact/P99zxLw4kyKr9p7XtPSgbF · source in `concept/` | v1, made before the review. Leads with events and travel; should shift to food and "what's new" like There San Diego. |
| Prototype site (Astro) | this folder (`src/`, `package.json`) | A rough prototype that runs. Built before planning, kept only as reference. |
| Writing, photo and fact-check rules plus a guide backlog | `CONTENT_GUIDE.md` | Draft |
| Licensed photo finder (Wikimedia Commons) | `scripts/find-image.mjs` → `npm run find-image -- "Congress Park Saratoga"` | Untested: the cloud session couldn't reach Commons |

Branch: `claude/heresaratoga-site` in `brxstudios/brxstudios`.

## What There San Diego is (summary of the review)

- One founder (Mike Cooch, There Media Group LLC, about 2016) plus freelancers. Mostly a house byline.
- **Recurring pages that keep one URL** and are rewritten on a schedule:
  - The Craving: weekly food column, Tuesdays
  - The Big List of Things to Do This Weekend: Thursdays
  - Things to Do This Month
  - Top Concerts This Week
  - New Restaurants Opening in 2026 (updated monthly)
- **Evergreen "Best X Right Now (2026 Guide)" pages** for search: restaurants, brunch, bars, rooftops, happy hours, patios, tacos and more. Plus day trips (Temecula, Julian, Big Bear), holiday guides, family/free stuff, and an events calendar (WordPress with what looks like The Events Calendar plugin). Tips come in by email (tips@); there's no event submission form.
- **Newsletter:** twice a week, Tuesday and Thursday, probably on Mailchimp. Claims about 20–30K subscribers. Instagram and Facebook have about 42K followers each. Claims 70K+ monthly unique visitors, 76% female, 75% aged 25–44.
- **Self-serve ad menu**, priced $97 / $297 / $497 / $997 / $1,500:
  - Sponsored Stories: they write the article and promote it with paid Facebook/Instagram ads, with guaranteed impressions. $497 for 10K, $997 for 25K, $1,500 for 50K per month.
  - Newsletter ads: $497 single, $997 for three, $1,500 for a dedicated email.
  - Instagram posts and giveaways: $497, $997 for three.
  - Deal ads and event boosts: $97–$497.
  - Business profile: $297 one-time.
- **Weaknesses:** stale pages, audience numbers that contradict each other, unclear labeling of sponsored posts.

## Saratoga plan (proposals, not final)

- **Names:**
  - **The Morning Line:** the newsletter, Tuesday and Thursday. It's a racing term; check for trademark or existing use.
  - **The Feedbag:** the weekly food column, the equivalent of The Craving.
  - **Track Season hub:** the biggest page and the biggest sales month.
- **Coverage:** all of Saratoga County (Ballston Spa, Wilton, Malta, Clifton Park, Schuylerville, Saratoga Lake), with the brand centered on Saratoga Springs. Day trips (Lake George, Adirondacks, Vermont, Cooperstown) play the role of Temecula.
- **Market:**
  - City population about 28.6K, county about 240K, Albany metro about 913K.
  - County visitor spending over $900M in 2024, with food and drink the largest category.
  - The 2026 track meet drew 1.05M paid admissions.
- **Competitors:** none hold this position.
  - Discover Saratoga has a 47K email list but serves the tourism bureau's members.
  - Saratoga.com is a directory.
  - Saratoga Living's Substack has about 4K subscribers, and its calendar is suspended.
  - The Saratogian has been cut back.
  - The largest Saratoga Instagram found is @aroundsaratogasprings, about 30K.
- **Openings:** a weekly newsletter for locals, a Saratoga openings tracker, and off-season content.
- **Starting prices** (assumptions, about 40–60% of San Diego's):
  - newsletter slot $99–199
  - sponsored story $249–399
  - deal/event ads $49 / $149 / $249
  - Track Season package $1,500–4,000
  - presenting sponsor $5–10K
  - raise prices 25–50% in summer
- **Timeline:**
  1. Build now.
  2. Soft launch in December 2026.
  3. Grow through the off-season, Jan–Mar.
  4. Pre-sell sponsors, Apr–May.
  5. 2027 track season, Jun–Labor Day. Confirm NYRA's 2027 dates; NYRA expects a return to a 40-day meet.

## Known Saratoga event dates (all to be confirmed)

- Victorian Streetwalk: expected Thu Dec 3, 2026 (first Thursday of December in recent years)
- Saratoga New Year's Fest (formerly First Night): Dec 31, 2026 – Jan 1, 2027
- Chowderfest: expected Sat Feb 6, 2027
- 2027 track meet: dates not announced. Travers usually falls on a late-August Saturday.

## Working preferences learned

- Joshua wants planning before building. Don't deploy or push anything live, and confirm before big build steps.
- Use licensed images only. Flag every AI-written fact for a person to check.
