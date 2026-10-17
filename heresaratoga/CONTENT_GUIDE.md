# HereSaratoga content playbook

How we write with AI, source photos and keep the guide trustworthy.

## 1. The voice

- Write like a local telling a friend what to do this weekend. Warm, specific, a little opinionated.
- Lead with the useful thing. Short paragraphs, real names, concrete tips ("get there when the gates open").
- No filler: no "nestled", "vibrant", "hidden gem", "something for everyone", "whether you're…or…".
- Brand: **cobalt blue** (`#0047AB`), Fraunces for headlines, Inter for body.

## 2. Writing a guide with AI

1. Pick a topic from the backlog below.
2. Gather sources first: official sites (venue, NYRA, SPAC, NY State Parks, Discover Saratoga), recent local news. Paste them into the prompt.
3. Use this prompt:

   > You are writing for HereSaratoga, the complete local guide to Saratoga Springs, NY. Voice: a knowledgeable local talking to a friend. Specific, warm, practical, no clichés.
   > Write a guide titled "{title}" in Markdown with H2/H3 sections, 600–1,200 words.
   > Use ONLY facts in the sources below. If a fact (hours, prices, dates, addresses) isn't in the sources, leave it out or say "check the venue's site". Never invent businesses, quotes, prices or dates.
   > Link to other HereSaratoga pages where relevant: /events/, /explore/things-to-do/, /explore/eat-drink/, /explore/stay/, /guides/{slug}/.
   > Sources: {paste}

4. Save as `src/content/guides/{slug}.md` with frontmatter (copy an existing guide). Leave `factChecked: false`.
5. **Fact-check before publishing.** A person checks every business name, date, price and claim against a live source, then sets `factChecked: true`. AI models confidently get local details wrong: closed restaurants, moved events, invented hours.
6. Update the `updated:` date whenever you revise a guide. Re-check seasonal guides each year.

## 3. Photos: the rules

"Sourcing from the internet" has to mean **licensed** photos. Grabbing images from Google, Instagram or other sites is copyright infringement, and photo agencies actively send demand letters to small publishers.

Use, in order of preference:

| Source | How | Credit |
|---|---|---|
| **Your own photos** | Best option. Shoot the places you write about. | "HereSaratoga" |
| **Wikimedia Commons** | `npm run find-image -- "Saratoga Spa State Park"`. The script only shows CC0 / CC BY / CC BY-SA / public domain and writes the credit for you. | Required, script fills it in |
| **Unsplash / Pexels** | Search "Saratoga Springs". Free for commercial use. | Credit the photographer (courtesy) |
| **Businesses & venues** | Ask for press photos by email; get a "yes, you can use these" in writing. | As they request |
| **Event submissions** | The submit form asks for photos the submitter has rights to. | As provided |

Every image needs `src`, `alt`, `credit`, `license` and `sourceUrl`. They're shown on the photo and listed on /about#photo-credits automatically. **Don't use AI-generated images of real places.** Readers notice and it undermines a travel guide.

## 4. Events

Edit `src/data/events.json`. Fields: `title`, `start` (YYYY-MM-DD), optional `end`, `time`, `venue`, `category`, `price`, `summary`, `url`.

- `dateConfirmed: false` shows a "Date TBC" badge. Use it for annual events whose date is predicted from past years, and flip it once the organizer announces.
- Past events drop off automatically **when the site rebuilds**, so schedule a daily rebuild (see README).
- Weekly sources to check: Discover Saratoga, SPAC, Caffè Lena, NYRA, Saratoga Arts, City of Saratoga Springs, Northshire events, Saratoga Living, the Daily Gazette and Times Union calendars, venue Instagrams.

## 5. Places (directory)

Edit `src/data/places.json`. Categories: `see`, `do`, `eat`, `drink`, `stay`, `shop`. Before adding a business, confirm it's open (recent reviews, its own site or social posts).

## 6. Guide backlog (priority order)

Tier 1, the pages people search for:
- Best restaurants in Saratoga Springs
- Where to stay in Saratoga (by budget and neighborhood)
- Things to do in Saratoga Springs (the master list)
- Saratoga Springs with kids
- Best brunch in Saratoga
- Saratoga bars & nightlife (Caroline Street guide)
- Track season: where to eat near the track / what to wear / how to bet for beginners
- Travers Weekend guide (update every year)
- Saratoga Lake guide
- Saratoga National Historical Park & the battlefield

Tier 2:
- Day trips: Lake George, the Adirondacks, Glens Falls, Vermont
- Free things to do in Saratoga
- Saratoga in fall (foliage, apple picking, Halloween)
- Saratoga in spring
- Dog-friendly Saratoga
- Coffee shops, bakeries, ice cream
- Golf in Saratoga
- Rainy-day Saratoga
- Saratoga history in 10 places
- Getting here: from NYC, Boston, Montreal; Amtrak; parking

Tier 3 (seasonal, rewrite yearly):
- Chowderfest survival guide · Victorian Streetwalk · New Year's in Saratoga · SPAC season preview · Opening weekend at the track · Holiday markets · Restaurant openings this month
