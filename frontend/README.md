# ProductAI frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4 + shadcn/ui + Framer Motion.
It talks only to its own route handler, which proxies the Python recommendation
service — the service URL never reaches the browser.

## Run

```bash
npm install
cp .env.example .env.local     # RECOMMENDER_API_URL, RECOMMENDER_TIMEOUT_MS
npm run dev                    # http://localhost:3000
```

The backend must be running (see `../backend/README.md`).

```bash
npx tsc --noEmit && npx eslint . && npm run build
```

## Layout

```
app/
  page.tsx                 landing + search form
  results/page.tsx         reads ?q= &r= &n=, redirects home if the query is unusable
  api/recommend/route.ts   validating proxy to the Python service
  error.tsx  not-found.tsx  loading.tsx
components/
  search-form.tsx          the three inputs, client-side validated with the shared zod schema
  results-view.tsx         request lifecycle: loading / error / empty / results
  recommendation-table.tsx desktop table (md and up)
  product-card.tsx         mobile cards (below md)
  loading-state.tsx        staged status + skeletons
  status-state.tsx         empty and error states
  results-header.tsx  hero.tsx  site-header.tsx
  theme-toggle.tsx  background-grid.tsx  score-meter.tsx  product-link.tsx
  ui/                      shadcn/ui primitives (button, input, textarea, select,
                           table, card, badge, tooltip, skeleton, separator, label)
lib/
  validation.ts            zod schemas shared by the form, the route handler and the client
  types.ts                 types inferred from those schemas
  api.ts                   browser -> /api/recommend
  recommendation-service.ts  server -> Python service (server-only)
  env.ts                   server-only configuration
  columns.ts               picks table columns from the fields the data actually has
  format.ts  utils.ts
```

## Notes

**Validation happens three times** — in the form (instant feedback), in the route
handler (`lib/validation.ts`), and again in the Python service. The route handler
and the browser client both parse the *response* too, so an upstream shape change
surfaces as a clean error state instead of a crash.

**Columns adapt to the data.** `lib/columns.ts` adds an attribute column only when at
least 60% of the returned products have that attribute, and hides the review count
when no product carries one — the scraped datasets are not uniform.

**Every product links out.** The Flipkart URL is used when the dataset has one;
otherwise the button opens a Flipkart search for the exact product title. Links are
`target="_blank"` with `rel="noopener noreferrer nofollow"`.

**Theme.** `next-themes` with `attribute="class"`, dark by default, persisted, no
flash on load. The toggle cross-fades sun and moon in CSS so the server and client
markup stay identical.

**Motion.** Framer Motion for the hero entrance, staggered result rows, the score
meters and state transitions. Every animated component checks `useReducedMotion()`,
and `globals.css` neutralises durations under `prefers-reduced-motion: reduce`.
