import { defineCollection, z } from 'astro:content';
import { glob, file } from 'astro/loaders';

const products = defineCollection({
    loader: glob({ pattern: "**/*.md", base: "../output" }),
    schema: z.object({
        product: z.string(),
        company: z.string(),
        rating: z.number().min(0).max(10),
        category: z.string(),
    }),
});

export const collections = { products };