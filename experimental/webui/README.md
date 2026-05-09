# SEAM WebUI (A-Web Browser Dashboard)

This is the browser dashboard / REST API GUI for SEAM, built with Vite + React + TypeScript.

## Quick Start

```bash
cd experimental/webui
npm install
npm run dev
```

Open http://localhost:5173 and configure the API base URL in **Settings** (default: `http://127.0.0.1:8765`).

## Build

```bash
npm run build
```

Outputs to `experimental/webui/dist/`.

## Requirements

- Node.js >= 18
- SEAM REST API running (e.g. `python seam.py serve --port 8765`)

## What works today

- **Status** — live `/health` polling and `/stats` (with bearer auth support)
- **Compile** — send text to `POST /compile`, view returned records
- **Search** — send query to `GET /search`, view ranked candidates
- **Context** — send query to `POST /context`, view candidates and pack output
- **Settings** — editable API base URL and bearer token stored in `localStorage` only

## Design

- Preserves the IDE-like shell from the original prototype
- Dark theme with JetBrains Mono typography
- Activity bar on the left, main pane on the right, status bar at the bottom
- UI states: disconnected, unauthorized, loading, success, error

## Notes

- The prototype backup lives in `experimental/webui/prototype-backup/`
- Keep secrets local; tokens are never committed
- This remains experimental until it has repeatable browser smoke tests
