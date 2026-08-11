# Personal Twin — Web UI

A polished React + TypeScript chat UI for the Personal Twin API. Streams answers over
SSE, shows the live pipeline (retrieve → generate → verify), renders inline clickable
`[n]` citations, and surfaces the retrieved sources with their similarity scores.

**Stack:** Vite · React 18 · TypeScript (strict) · Tailwind CSS. No UI-component or
icon-library dependencies — just React and Tailwind.

## Develop

```bash
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/chat`, `/ingest`, and `/health` to `http://localhost:8000`
(see `vite.config.ts`), so just run the backend (`uv run twin serve` in the repo root)
alongside it — no CORS or env config needed.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite dev server with API proxy |
| `npm run build` | Type-check (`tsc -b`) + production bundle to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run typecheck` | Strict type-check, no emit |
| `npm run format` | Prettier |

## Configuration

`VITE_API_BASE` (see `.env.example`) sets the API origin. Leave it empty for same-origin
requests (dev proxy, or the nginx proxy in the Docker image); set it only when the API
lives on a different host.

## Customising the twin

Edit `src/persona.ts` — name, role, tagline, monogram initials, and the starter
questions. That one file re-skins the UI for a different person or a company knowledge base.

## Design notes

- **Theme:** dark-first "AI console" with a violet→cyan accent, plus a light theme. Both
  are driven by CSS custom properties in `src/index.css`; the toggle persists to
  `localStorage` and respects `prefers-color-scheme` on first load.
- **Streaming:** `fetch` + a `ReadableStream` reader (native `EventSource` can't POST).
  The SSE protocol lives in `src/lib/sse.ts` as pure, framework-free functions.
- **Accessibility:** semantic landmarks, labelled controls, visible focus rings, keyboard
  send (Enter / Shift+Enter), and `prefers-color-scheme` support.

## Docker

Built and served by nginx (which also proxies the API, so the browser makes same-origin
requests). Runs as the `web` service in the repo's `compose.yaml` on port 3000.
