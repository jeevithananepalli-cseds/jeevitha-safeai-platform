# SafeAI — Frontend

Next.js (App Router) + TypeScript + Tailwind CSS client for SafeAI.
See the top-level [`README.md`](../README.md) and [`docs/`](../docs).

## Layout

```
src/
  app/                 # App Router pages (layout.tsx, page.tsx, globals.css)
  components/          # React components (e.g. BackendStatus)
  lib/api/             # typed API client + wire types mirroring the contract
```

The `lib/api` layer is the single, typed boundary to the backend: `client.ts`
wraps `fetch` and unwraps the `{ success, data, error }` envelope; `types.ts`
mirrors [`../docs/api-contract.md`](../docs/api-contract.md).

## Local development

```bash
# from frontend/
npm install
npm run dev          # http://localhost:3000
```

The client reads the API base URL from `NEXT_PUBLIC_API_BASE_URL`
(default `http://localhost:8000/api/v1`). Run the backend (or `docker compose up`
from the repo root) so the status panel on the home page reports "Backend ready".

## Quality gate

```bash
npm run lint         # eslint (next/core-web-vitals + next/typescript)
npm run typecheck    # tsc --noEmit
npm run build        # production build (fails on type/lint errors)
```
