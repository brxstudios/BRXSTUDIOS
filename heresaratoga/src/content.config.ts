import { defineCollection, z } from 'astro:content';
import { glob, file } from 'astro/loaders';

// Every photo must carry its credit + license. See CONTENT_GUIDE.md.
const image = z.object({
  src: z.string(),
  alt: z.string(),
  credit: z.string(),
  license: z.string(),
  sourceUrl: z.string().url(),
});

const guides = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/guides' }),
  schema: z.object({
    title: z.string(),
    dek: z.string(),
    category: z.enum(['Track Season', 'Things to Do', 'Eat & Drink', 'Stay', 'Outdoors', 'History', 'Itineraries', 'Arts & Music']),
    updated: z.coerce.date(),
    featured: z.boolean().default(false),
    image: image.optional(),
    // Flip to true only after a human has checked every fact, name and hour.
    factChecked: z.boolean().default(false),
  }),
});

const events = defineCollection({
  loader: file('./src/data/events.json'),
  schema: z.object({
    title: z.string(),
    start: z.coerce.date(),
    end: z.coerce.date().optional(),
    // false = expected date based on past years; shows a "Date TBC" badge.
    dateConfirmed: z.boolean().default(true),
    time: z.string().optional(),
    venue: z.string(),
    category: z.enum(['Festival', 'Music', 'Track', 'Food & Drink', 'Arts', 'Family', 'Holiday', 'Outdoors']),
    price: z.string().default('Free'),
    summary: z.string(),
    url: z.string().url().optional(),
    featured: z.boolean().default(false),
  }),
});

const places = defineCollection({
  loader: file('./src/data/places.json'),
  schema: z.object({
    name: z.string(),
    category: z.enum(['see', 'do', 'eat', 'drink', 'stay', 'shop']),
    area: z.string(),
    blurb: z.string(),
    tags: z.array(z.string()).default([]),
    seasonal: z.string().optional(),
    url: z.string().url().optional(),
    image: image.optional(),
  }),
});

export const collections = { guides, events, places };
