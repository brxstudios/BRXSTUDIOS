export const SITE = {
  name: 'HereSaratoga',
  tagline: 'The complete guide to Saratoga Springs',
  description:
    'Where to eat, what to do, where to stay and what’s happening in Saratoga Springs, NY — from track season to Chowderfest.',
  email: import.meta.env.PUBLIC_CONTACT_EMAIL || 'hello@heresaratoga.com',
  eventFormEndpoint: import.meta.env.PUBLIC_EVENT_FORM_ENDPOINT || '',
  newsletterEndpoint: import.meta.env.PUBLIC_NEWSLETTER_ENDPOINT || '',
};

export const NAV = [
  { href: '/events/', label: 'Events' },
  { href: '/guides/', label: 'Guides' },
  { href: '/explore/things-to-do/', label: 'Things to Do' },
  { href: '/explore/eat-drink/', label: 'Eat & Drink' },
  { href: '/explore/stay/', label: 'Stay' },
  { href: '/explore/shop/', label: 'Shop' },
];

export type PlaceCategory = 'see' | 'do' | 'eat' | 'drink' | 'stay' | 'shop';

// Directory sections: each page groups one or more place categories.
export const SECTIONS: Record<string, { title: string; intro: string; groups: { cat: PlaceCategory; heading: string }[] }> = {
  'things-to-do': {
    title: 'Things to Do in Saratoga',
    intro: 'Racing, music, the lake, the springs, museums and the landmarks that make Saratoga Saratoga.',
    groups: [{ cat: 'do', heading: 'Do' }, { cat: 'see', heading: 'See' }],
  },
  'eat-drink': {
    title: 'Where to Eat & Drink',
    intro: 'From fried chicken institutions and Broadway bakeries to the taprooms that fill up after the last race.',
    groups: [{ cat: 'eat', heading: 'Eat' }, { cat: 'drink', heading: 'Drink' }],
  },
  stay: {
    title: 'Where to Stay in Saratoga',
    intro: 'Grand hotels, park-side stays and inns within walking distance of Broadway. For track season, book months ahead.',
    groups: [{ cat: 'stay', heading: 'Hotels & Inns' }],
  },
  shop: {
    title: 'Where to Shop',
    intro: 'Broadway boutiques, bookstores and the shops worth bringing home a bag from.',
    groups: [{ cat: 'shop', heading: 'Shops' }],
  },
};

export const CATEGORY_LABEL: Record<PlaceCategory, string> = {
  see: 'See', do: 'Do', eat: 'Eat', drink: 'Drink', stay: 'Stay', shop: 'Shop',
};
