# There San Diego (theresandiego.com): Editorial Content and Site Structure

Method note (read first): theresandiego.com, offers.theresandiego.com and advertise.theresandiego.com all failed DNS from this environment (`getaddrinfo ENOTFOUND`). No page was fetched directly. All findings come from web-search result titles, URLs, and the search engine's summaries of indexed page text, gathered 2026-10-19. Titles and URLs are reliable. Quoted details (prices, cadences, subscriber counts) are the search engine's paraphrases of page text and should be checked against the live site. Several summaries noted that page-age metadata conflicts with dates printed in the pages.

## 1. Navigation categories, sections, and homepage

### Takeaway
The site is organized around a few hub/archive pages: Eat + Drink, See/Do/Events, Guides, Free & Easy, Giveaways, an Events archive (`/event/`), venue pages (`/venue/`), and location taxonomies (`/location/`). The homepage title is "There San Diego - Things To Do In San Diego". I could not see the homepage's module order.

### Cited Findings
- Homepage title: "There San Diego - Things To Do In San Diego". — [theresandiego.com](https://theresandiego.com/)
- Hub page "Eat + Drink" is the home of The Craving, described as "the weekly guide to what's worth eating and drinking in San Diego right now". — [Eat + Drink](https://theresandiego.com/eat-drink/)
- Hub page titled "The Best Things To Do In San Diego" at slug `/see-do-events/`, which is the things-to-do/events section. — [See Do Events](https://theresandiego.com/see-do-events/)
- "Guides" hub page. — [Guides](https://theresandiego.com/guides/)
- "Free & Easy" section page. — [Free & Easy](https://theresandiego.com/free-easy/)
- "Giveaways" section page. — [Giveaways](https://theresandiego.com/giveaway/)
- "Events Archive" at `/event/`. Individual events live at `/event/<slug>/`. — [Events Archive](https://theresandiego.com/event/)
- Venue pages exist at `/venue/<slug>/`, e.g. "Lana's Opening Marks Significant Addition to Solana Beach". — [Venue page](https://theresandiego.com/venue/lana-solana-beach-opening/)
- Location taxonomy "San Diego Archives" at `/location/san-diego/`. — [Location archive](https://theresandiego.com/location/san-diego/)
- Utility pages: About Us, Contact Us, Contest/Sweepstakes Rules, Restaurant Packages, Packages (advertising). — [About](https://theresandiego.com/about/); [Contact Us](https://theresandiego.com/contactus/); [Contest Rules](https://theresandiego.com/contest-sweepstakes-rules/); [Restaurant Packages](https://theresandiego.com/restaurant-packages/); [Packages](https://theresandiego.com/packages/)
- A search summary reported that the navigation menu includes "Advertise With Us", "Send Us A Tip", "About Us" and newsletter links. This comes from the search engine's summary, not a fetched page. — [theresandiego.com](https://theresandiego.com/)
- The homepage paginates deeply, e.g. `/page/192/`, which implies a long reverse-chronological post feed (roughly 192+ pages). — [Page 192](https://theresandiego.com/page/192/?mc_eid=2f19e94ec8)
- Profile series "SD Originals", e.g. "Meet San Diego Original Dave Hackett - Skater, Stunt Man, Artist & Entrepreneur". There is also a founder-profile post, "Meet First Light Coffee Whiskey Founder Ryan Espi". — [SD Originals: Hackett](https://theresandiego.com/sd-originals-hackett-dave/); [Ryan Espi](https://theresandiego.com/meet-first-light-coffee-whiskey-founder-ryan-espi/)

### Inferences
- The top-level navigation is probably Eat + Drink / See + Do (Events) / Guides / Free & Easy / Giveaways, plus Newsletter / Tip / Advertise. This is inferred from the hub slugs. The actual menu labels are unconfirmed.
- The homepage is probably a latest-posts feed plus featured modules (weekend list, The Craving, guides). This is inferred from the deep `/page/N/` pagination. The actual order is unknown.

### Gaps
- I could not confirm the homepage module order, the exact menu labels, or whether Family or Day Trips are menu items. Neighborhood guides exist (North Park), but I found no neighborhood index page.

## 2. Recurring series and columns

### Takeaway
There are four main recurring series, all evergreen-URL "living" posts that are updated on a schedule:
- The Craving (weekly food and drink, Tuesdays)
- The Big List of Things to Do This Weekend (weekly, tied to a Thursday newsletter)
- Things to Do This Month
- Top Concerts This Week

The monthly "New Restaurants Opening in 2026 (Updated Monthly)" tracker is also recurring. Seasonal "Big List" holiday roundups repeat each year.

### Cited Findings
- **The Craving**: "What to Eat and Drink in San Diego This Week", a single evergreen URL. Per the search summaries, it is published every Tuesday and covers new restaurant openings, standout happy hours, limited-time menu specials, game-day specials, and upcoming food events. Editions carry "Week of ..." headers. Editions referenced include Aug 3, Aug 17, Aug 24, Sep 7, Sep 21, Sep 28, Oct 5 and Oct 12, 2026. Sample items: Juliette (Little Italy, opening fall), Maranello's pepperoni-infused gin Negroni, Chula Vista Farmers' Market expanding to 100+ tents, Playa Kitchen La Jolla (coffee from $2.50), and Lana Solana Beach (437 S Hwy 101). — [The Craving](https://theresandiego.com/the-craving-san-diego-restaurants-and-bars/); [Eat + Drink](https://theresandiego.com/eat-drink/)
- **Weekend list**: "The Big List of Things to Do in San Diego This Weekend", an evergreen URL updated weekly ("Week of October 15" seen). Per its page text: "Every week, we round up San Diego's best weekend plans and send them to 25,000 locals... free in your inbox every Thursday." An older variant slug and older dated event-post versions exist. — [This Weekend](https://theresandiego.com/things-to-do-in-san-diego-this-weekend/); [older variant](https://theresandiego.com/things-to-do-in-san-diego-weekend/); [dated legacy version, Mar 23–26](https://theresandiego.com/event/the-great-big-list-of-things-to-do-this-weekend-in-san-diego-march23-march26/)
- **Monthly list**: "Things to Do in San Diego in October" at the evergreen slug `/things-to-do-in-san-diego-this-month/`. The title is retitled each month. October items include Mission Bayfest (Oct 16–18) and Coffee Festival/Harvest Fest (Oct 10–11). — [This Month](https://theresandiego.com/things-to-do-in-san-diego-this-month/)
- **Weekly concerts**: "Top Concerts in San Diego This Week". — [Concerts](https://theresandiego.com/concerts-in-san-diego-this-week/)
- **Monthly openings tracker**: "New Restaurants Opening in San Diego in 2026 (Updated Monthly)". Search summaries say it counted 24 spots as of early August. Listings include El Punto at Liberty Station (Oct 2026), Juliette, Moniker General (WEST tower, late 2026), Heritage Steakhouse in Santee (Nov), Zuma at the Guild Hotel, Sugarfish Little Italy, À L'ouest North Park, and Fleurette in La Jolla. — [New Restaurants 2026](https://theresandiego.com/new-restaurants-opening-in-san-diego-in-2026/)
- Related opening coverage: "Three Major Restaurant Openings to Watch This Year"; "Explore The Valley's New Wave of Openings". One article says 2026 is "tracking toward 90+ restaurant and bar openings". — [Three Major](https://theresandiego.com/three-major-restaurant-openings-in-san-diego/); [Valley openings](https://theresandiego.com/valley-mission-valley-new-openings/)
- **Newsletter cadence**: the About page states the newsletter goes out Tuesday and Thursday, per the search summary. — [About](https://theresandiego.com/about/)
- **SD Originals** profile series (cadence unknown). — [SD Originals](https://theresandiego.com/sd-originals-hackett-dave/)
- "Escapes:" prefix used for getaway guides, e.g. "Escapes: Your Guide to a Perfect Idyllwild Getaway". This may be a series label. — [Idyllwild](https://theresandiego.com/san-diego-road-trip-guide-to-idyllwild/)

### Inferences
- The core model is "evergreen URL, overwritten weekly or monthly". The recurring posts keep a fixed slug (e.g. `/this-weekend/`, `/this-month/`) so they build SEO authority, and each newsletter links back to them. Older practice (around 2017–2019) used new dated URLs per weekend under `/event/`. They have since moved away from that.

### Gaps
- I could not see whether past Craving editions are archived separately or overwritten. I also could not find the bylines or authors of the columns.

## 3. Evergreen and SEO pages (titles and URLs grouped by type)

### Takeaway
A strong set of "(2026 Guide)" / "Right Now" titled food and drink pillar pages, a "Local's Guide" things-to-do pillar, a neighborhood guide, and many seasonal and holiday listicles. Many legacy listicles are years old.

### Cited Findings
**Food and drink pillars ("Right Now (2026 Guide)" format)**
- The Best Restaurants in San Diego Right Now (2026 Guide). Marked "Last updated: October 2026". Soichi is its top omakase pick, and Callie in East Village is "the answer it gives most often". — [link](https://theresandiego.com/best-restaurants-in-san-diego/)
- The Best Brunch in San Diego Right Now (2026 Guide). — [link](https://theresandiego.com/the-best-brunch-in-san-diego-right-now-2026-guide/)
- The Best Bars in San Diego Right Now (2026 Guide). — [link](https://theresandiego.com/the-best-bars-in-san-diego-right-now-2026-guide/)
- The Best Rooftop Bars in San Diego Right Now (2026 Guide). — [link](https://theresandiego.com/the-best-rooftop-bars-in-san-diego-right-now/)
- The Best Cocktail Bars in San Diego Right Now (2026 Guide). — [link](https://theresandiego.com/the-best-cocktail-bars-in-san-diego-right-now/)
- New Restaurants Opening in San Diego in 2026 (Updated Monthly). — [link](https://theresandiego.com/new-restaurants-opening-in-san-diego-in-2026/)
- San Diego's Best Happy Hours: Where to Eat, Drink & Watch the Sunset This Summer. — [link](https://theresandiego.com/san-diegos-best-happy-hours/)
- The Best Nightclubs in San Diego: Gaslamp and Downtown. — [link](https://theresandiego.com/the-best-nightclubs-in-san-diego-gaslamp-and-downtown/)
- Which Restaurants and Bars Have the Best Outdoor Patios in San Diego? The Votes Are In... (reader-vote format). — [link](https://theresandiego.com/best-outdoor-patios-in-san-diego/)
- Top Ten Best Patios To Eat And Drink In Downtown San Diego (older). — [link](https://theresandiego.com/top-ten-best-patios-to-eat-drink-in-downtown-san-diego/)
- Where to Get the Best Burgers in San Diego. — [link](https://theresandiego.com/the-best-burgers-in-san-diego/)
- San Diego's Ultimate Food Truck Guide. — [link](https://theresandiego.com/best-food-trucks-in-san-diego/)
- 7 Must-Try San Diego Taco Stands To Explore For Taco Tuesday. — [link](https://theresandiego.com/san-diego-taco-tuesday/)
- Guide to the Best Restaurants in Old Town San Diego. — [link](https://theresandiego.com/guide-to-the-best-restaurants-in-old-town-san-diego/)
- Not Sleeping? Neither Are These San Diego Restaurants (late-night). — [link](https://theresandiego.com/not-sleeping-neither-are-these-san-diego-restaurants/)
- Where to Eat and Drink Before (and After) a Padres Game. — [link](https://theresandiego.com/where-to-eat-and-drink-before-and-after-a-padres-game/)
- 9 of the Best Views in San Diego. — [link](https://theresandiego.com/9-of-the-best-views-in-san-diego/)
- Outdoor Dining Updates From Your Favorite San Diego Restaurants (COVID-era, outdated). — [link](https://theresandiego.com/outdoor-dining-san-diego-restaurants/)

**Things-to-do pillars**
- Things to Do in San Diego: The Local's Guide (2026). — [link](https://theresandiego.com/things-to-do-in-san-diego/)
- 18 Unique and Fun Things to Do in San Diego. — [link](https://theresandiego.com/fun-things-to-do-in-san-diego/)
- 16 Romantic Date Ideas in San Diego That Aren't Going to a Restaurant. — [link](https://theresandiego.com/romantic-date-ideas-in-san-diego/)
- 7 Ways to Experience Winter in San Diego. — [link](https://theresandiego.com/7-ways-to-experience-winter-in-san-diego/)

**Neighborhood**
- North Park San Diego: The Complete Neighborhood Guide (2026). — [link](https://theresandiego.com/north-park-san-diego-the-complete-neighborhood-guide/)

**Day trips and getaways**
- 17 Amazing Road Trips From San Diego. — [link](https://theresandiego.com/17-road-trips-from-san-diego/)
- 14 Must-Do Day Trips from San Diego. — [link](https://theresandiego.com/14-must-do-day-trips-near-san-diego/)
- Six Great Destinations for a Fall Road Trip From San Diego. — [link](https://theresandiego.com/6-san-diego-day-trips-for-a-fall-feeling/)
- Escapes: Your Guide to a Perfect Idyllwild Getaway. — [link](https://theresandiego.com/san-diego-road-trip-guide-to-idyllwild/)
- Your Guide To A Fall Day In Julian; Road Trip To Julian; Sledding is only an hour away...take a day trip to Julian! — [Fall Julian](https://theresandiego.com/a-day-trip-to-julian/); [Road trip Julian](https://theresandiego.com/road-trip-to-julian/); [Sledding](https://theresandiego.com/sledding-hour-away/)
- The 7 Best Places in the San Diego Area to See the Fall Leaves. — [link](https://theresandiego.com/the-7-best-places-in-the-san-diego-area-to-see-the-fall-leaves/)
- Big Bear Fall Weekend Events for a Great Getaway. — [link](https://theresandiego.com/big-bear-fall-weekend-events-for-a-great-getaway/)
- Explore Temecula Valley's Barrel Art Trail (42 sculptures). — [link](https://theresandiego.com/temecula-valley-barrel-art-trail/)

**Seasonal and holiday**
- Halloween in San Diego: Events, Food, Drinks, & Fun Happenings, also titled "Halloween and Día de los Muertos Celebrations and Specials in San Diego". — [link](https://theresandiego.com/san-diego-halloween-events-food-drinks-and-fun/)
- The Best Pumpkin Patches in and Around San Diego. — [link](https://theresandiego.com/your-guide-to-the-best-pumpkin-patches-in-and-around-san-diego/)
- The Big List of Places to Eat for Thanksgiving In San Diego (may be a prior year's version). — [link](https://theresandiego.com/the-great-big-list-of-places-to-enjoy-a-thanksgiving-feast-san-diego/)
- The 11 Best Neighborhoods to See Christmas Lights in San Diego. — [link](https://theresandiego.com/top-neighborhoods-to-view-christmas-lights-in-san-diego/)
- 12 Things to Do for the Holidays That are Uniquely San Diego (plus an older "11 Things" version). — [12](https://theresandiego.com/things-to-do-for-the-holidays-in-san-diego/); [11](https://theresandiego.com/11-things-to-do-for-the-holidays-that-are-uniquely-san-diego/)
- Countdown to 2026: San Diego's Must-Hit NYE Parties. Outdated as of Oct 2026, since it targets NYE 2025. — [link](https://theresandiego.com/nye-parties-san-diego/)
- The Best New Year's Eve Dinners and 'Recovery Brunches' to Ring In 2026. Outdated, same reason. — [link](https://theresandiego.com/new-years-eve-dinner-san-diego-restaurants/)
- 11 Romantic Valentine's Day Date Ideas in San Diego. — [link](https://theresandiego.com/11-romantic-valentines-day-date-ideas-in-san-diego/)
- Nine Great Ways To Celebrate 4th Of July In San Diego. — [link](https://theresandiego.com/nine-great-ways-to-celebrate-4th-of-july-in-san-diego/)
- Ring in the Holidays With Salute the Season at Liberty Station. — [link](https://theresandiego.com/liberty-station-holiday-magic-at-salute-the-season/)
- Catch Three Holiday Shows at the Old Globe This Season. — [link](https://theresandiego.com/old-globe-theatre-holiday-shows/)

**Family and free**
- Bring the Kids to 60+ Museums Free This October (2026, now includes Tijuana venues), plus the prior year's version "Unlock Adventure as Kids Go Free at 50+ San Diego Museums This October". — [2026](https://theresandiego.com/kids-free-october-san-diego-museum-council/); [prior](https://theresandiego.com/kids-free-san-diego-museum-council/)
- Enriching Summer Art Adventures for Kids & Families at SDMA. — [link](https://theresandiego.com/san-diego-museum-art-summer-art-adventures/)
- Spend October Outside With Nature Collective: Free Tours, a Fall Festival & a Way to Give Back. — [link](https://theresandiego.com/nature-collective-fall-events/)

**News and opening posts (single-venue)**
- Lana in Solana Beach; Kura Revolving Sushi Bar Grand Opening; Rare Society Solana Beach (open, happy hour); North Italia at One Paseo; Juliette Opens in Little Italy This Fall; Tierra y Mar at Harrah's; Acqua E Farina in Chula Vista; Playa Kitchen La Jolla; Dora Ristorante Tre Forchette; Compound Lifting Club Solana Beach; Breathe Degrees Liberty Station; Leucadia Listening Lounge; The Conrad resident companies. — [Lana](https://theresandiego.com/lana-solana-beach-restaurant-highway-101/); [Kura](https://theresandiego.com/kura-revolving-sushi-bar-grand-opening/); [Rare Society](https://theresandiego.com/rare-society-solana-beach-open/); [Rare Society HH](https://theresandiego.com/rare-society-happy-hour-solana-beach/); [North Italia](https://theresandiego.com/north-italia-one-paseo-now-open/); [Juliette](https://theresandiego.com/juliette-restaurant-little-italy-your-next-night-out-spot/); [Tierra y Mar](https://theresandiego.com/tierra-y-mar-restaurant-restaurant-harrahs-resort-socal/); [Acqua E Farina](https://theresandiego.com/acqua-e-farina-trattoria-romana-chula-vista/); [Playa Kitchen](https://theresandiego.com/playa-kitchen-la-jolla/); [Dora](https://theresandiego.com/dora-ristorante-tre-forchette-2026-dining-excellence/); [Compound](https://theresandiego.com/compound-lifting-club-solana-beach/); [Breathe Degrees](https://theresandiego.com/breathe-degrees-liberty-station-now-open-in-san-diego/); [Leucadia](https://theresandiego.com/leucadia-listening-lounge/); [Conrad](https://theresandiego.com/resident-companies-at-the-conrad-bring-vibrant-talent/)

### Inferences
- The SEO pattern is a "[Best X] in [City] Right Now ([Year] Guide)" title, a stable slug (sometimes containing the year), and a "Last updated: [Month Year]" stamp. A Saratoga equivalent could be "Best Restaurants in Saratoga Springs Right Now (2027 Guide)", "New Restaurants Opening in Saratoga in 2027 (Updated Monthly)", "Things to Do in Saratoga: The Local's Guide", and "Things to Do in Saratoga in [Month]".
- Holiday posts are republished yearly. Sometimes the slug is reused (Halloween) and sometimes a new one is created (Kids Free), which leaves duplicates.

### Gaps
- I found only one neighborhood guide (North Park). I found no general La Jolla, Encinitas or Gaslamp guides in the index. No standalone "best tacos" or "best coffee" pillar surfaced.

## 4. Events coverage

### Takeaway
Events are handled with a WordPress events-calendar structure: an `/event/` archive, single event posts and `/venue/` pages. Weekly, monthly and seasonal "Big List" roundups sit on top of that. Readers and venues submit through tips@theresandiego.com.

### Cited Findings
- Events archive at `/event/`. — [Events Archive](https://theresandiego.com/event/)
- Example single event posts: "Exclusive Evening Access To SD Museum Of Art At #ArtAfterHours"; "A Special Haunted Halloween At The North Park Thursday Market"; "Urban Halloween Magic at Little Italy's Trick-or-Treat on India Street"; "Halloween Family Day At The San Diego Natural History Museum"; "Join The 'Sweat For Service' Workout On The USS Midway"; "Got A Poetic Side? Hit Up This San Diego Poetry Slam Qualifier!"; "San Diego Startup Week"; the OMBAC Over The Line craft beer festival; San Diego FC's Inaugural Match Watch Party. — [Art After Hours](https://theresandiego.com/event/exclusive-evening-access-sd-museum-art-art-after-hours/); [North Park Halloween](https://theresandiego.com/event/haunted-halloween-north-park-thursday-market/); [Little Italy](https://theresandiego.com/event/little-italy-halloween-trick-or-treat-on-india-street/); [NAT](https://theresandiego.com/event/halloween-family-day-san-diego-nat/); [Midway](https://theresandiego.com/event/sweat-for-service-workout-on-the-uss-midway/); [Poetry Slam](https://theresandiego.com/event/san-diego-poetryslam-5th-qualifier/); [Startup Week](https://theresandiego.com/event/san-diego-startup-week/); [OMBAC](https://theresandiego.com/event/ombac-hosting-craft-beer-festival-line-tournament/); [SDFC](https://theresandiego.com/event/san-diego-fc-first-ever-match-watch-party/)
- Bare-name event listings, which look like automated or ticketing feeds: "Dread Mar I", "Chris Tomlin", "Asian Street Food", "Lola Demure's Burlesque & Variety Show". — [Dread Mar I](https://theresandiego.com/event/dread-mar-i/); [Chris Tomlin](https://theresandiego.com/event/chris-tomlin/); [Asian Street Food](https://theresandiego.com/event/asian-street-food/); [Lola Demure](https://theresandiego.com/event/lola-demures-burlesque-variety-show-2/)
- Many event posts are dated: SD Loyal 2022 Fan Appreciation Day, the 2023 Homebrew Con. — [SD Loyal](https://theresandiego.com/event/sd-loyal-2022-fan-appreciation-day/); [Homebrew Con](https://theresandiego.com/event/2023-homebrew-con-san-diego/)
- Contact page, per the search summary: tips@theresandiego.com for "hot tips about an event or venue"; sales@theresandiego.com for advertising. — [Contact Us](https://theresandiego.com/contactus/)
- Roundups: weekend Big List, monthly list, weekly concerts, and holiday Big Lists (see sections 2 and 3).

### Inferences
- The `/event/` and `/venue/` slug pair matches the default permalinks of The Events Calendar (Modern Tribe/StellarWP) WordPress plugin. This is likely but unconfirmed.
- The bare artist-name listings suggest an imported or automated event feed alongside the editorial event posts.

### Gaps
- I could not confirm a public event-submission form, whether submissions are free or paid, or whether the calendar has a filterable grid or list view.

## 5. Voice, style, length, photos, sponsored labeling

### Takeaway
The voice is a casual, first-person-plural local insider ("we round up", "the answer we give most often"), with punchy title-case headlines that often include numbers. Commercial content is a core product: Sponsored Stories, newsletter ads and deals. How it is labeled on the page is unverified.

### Cited Findings
- Insider voice: "Every week, we round up San Diego's best weekend plans and send them to 25,000 locals." — [This Weekend](https://theresandiego.com/things-to-do-in-san-diego-this-weekend/)
- Opinionated and practical guide copy. Examples from the search summaries: The Taco Stand "always has a line, and the line always moves fast"; Soichi is "not cheap and you should book weeks ahead"; Little Italy's Saturday market advice is to arrive before 11 AM; the Gaslamp is "Loud, expensive, and fun". — [Best Restaurants](https://theresandiego.com/best-restaurants-in-san-diego/); [North Park](https://theresandiego.com/north-park-san-diego-the-complete-neighborhood-guide/); [Things to Do](https://theresandiego.com/things-to-do-in-san-diego/)
- Listing entries include practical details such as hours, prices and addresses, e.g. Lana at 437 S Hwy 101 with weekday hours of 4–10 PM, and Los Panchos' $25 bottomless mimosas. — [The Craving](https://theresandiego.com/the-craving-san-diego-restaurants-and-bars/); [Brunch](https://theresandiego.com/the-best-brunch-in-san-diego-right-now-2026-guide/)
- Headline style: clickbait-light ("Not Sleeping? Neither Are These San Diego Restaurants", "Got A Poetic Side?"), plus numbered listicles ("17 Amazing Road Trips"). — [Not Sleeping](https://theresandiego.com/not-sleeping-neither-are-these-san-diego-restaurants/); [17 Road Trips](https://theresandiego.com/17-road-trips-from-san-diego/)
- Sponsored Stories product: "we write a professionally crafted article about your business, publish it on ThereSanDiego.com, and promote it with targeted Facebook and Instagram ads". Search summaries reported tiers of $497, $997 (citywide) and $1,500 (countywide). — [Sponsored Stories](https://offers.theresandiego.com/SponsoredStories-page)
- Many single-venue posts read as promotional, e.g. "Catch San Diego's Best Performing Arts at The Conrad" and "Breathe Degrees Just Opened a Second Location". — [Conrad](https://theresandiego.com/resident-companies-at-the-conrad-bring-vibrant-talent/); [Breathe Degrees](https://theresandiego.com/breathe-degrees-liberty-station-now-open-in-san-diego/)
- Giveaways run on a separate sweepstakes subdomain, e.g. "Win VIP 2-Day Passes to the Del Mar Wine & Food Festival!", with a contest rules page. — [Sweepstakes](https://sweepstakes.theresandiego.com/delmarwinefoodfestival); [Rules](https://theresandiego.com/contest-sweepstakes-rules/)

### Inferences
- Paid venue features and editorial look similar in title style. Whether a "Sponsored" tag appears could not be verified.

### Gaps
- Article word counts, photo counts and sources (original vs. venue-supplied), bylines, and on-page sponsored disclosures could not be checked without fetching pages.

## 6. Tech platform and business hints

### Takeaway
The site is very likely WordPress with an events-calendar plugin and Mailchimp email. The offers, advertise and sweepstakes subdomains are separate landing-page and sales tools; the builder is unconfirmed, though its sales-calendar page mentions lead-management software.

### Cited Findings
- WordPress-style URL patterns: `/page/192/`, `/location/san-diego/`, `/event/`, `/venue/`. — [Page 192](https://theresandiego.com/page/192/?mc_eid=2f19e94ec8); [Location](https://theresandiego.com/location/san-diego/)
- An `mc_eid` query parameter is present in an indexed URL. This is Mailchimp's subscriber-tracking parameter, which suggests the newsletter is sent with Mailchimp. — [Page 192](https://theresandiego.com/page/192/?mc_eid=2f19e94ec8)
- The offers subdomain pages are Social (`/social`), Deals (`/get-deals-page`), Newsletter Ads (`/newsletter-ads-page`), Sponsored Stories (`/SponsoredStories-page`) and Sales Calendar (`/calendar`). Search summaries reported: Deals at $97/mo (5,000 impressions) and $297/mo (20,000), dated Oct 13, 2022; Newsletter ads at "nearly 30,000+" subscribers, $497 single, $997 for three, $1,500 dedicated; sales contact sales@theresandiego.com, 619.361.7484. The calendar page reportedly contains stray text about lead-management software and a "$15 per-shipment subscription", which looks like leftover template content. — [Social](https://offers.theresandiego.com/social); [Deals](https://offers.theresandiego.com/get-deals-page); [Newsletter Ads](https://offers.theresandiego.com/newsletter-ads-page); [Calendar](https://offers.theresandiego.com/calendar); [Sponsored Stories](https://offers.theresandiego.com/SponsoredStories-page)
- Separate advertising site: "Advertise with ThereSanDiego.com", which positions the site as "San Diego's go-to guide for locals to find the best things to eat, drink, see, and do". — [Advertise](https://advertise.theresandiego.com/)
- Subscriber claims vary: 25,000+ on editorial pages, "nearly 30,000+" on the ad page. — [This Weekend](https://theresandiego.com/things-to-do-in-san-diego-this-weekend/); [Newsletter Ads](https://offers.theresandiego.com/newsletter-ads-page)
- Facebook presence: @theresandiego. — [Facebook](https://www.facebook.com/theresandiego/)

### Inferences
- The offers subdomain's "-page" slug suffixes, the booking calendar, and the generic lead-management or template text are consistent with an all-in-one funnel builder such as GoHighLevel, ClickFunnels or Systeme. This is speculation, not verified.

### Gaps
- Unverified: the WordPress theme, the specific events plugin, the funnel builder, and the founder or ownership. I found no source naming the founder, and the "Dave Good" query returned unrelated people. The About page content was not retrievable.
