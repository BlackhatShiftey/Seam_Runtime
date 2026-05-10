# SEAM WebUI (A-Web Browser Dashboard)

This is the browser dashboard / REST API GUI for SEAM, built with Vite + React + TypeScript.

## Quick Start

```bash
cd experimental/webui
npm install
npm run dev
```

Open http://localhost:5173. The root app currently serves the preserved original IDE-like prototype from `prototype-backup/` so the graphs, settings, terminal, and chat stay visible while the REST-wired TypeScript panes are reworked.

## Build

```bash
npm run build
```

Outputs to `experimental/webui/dist/`.

## Requirements

- Node.js >= 20.19 or >= 22.12
- SEAM REST API running (e.g. `python seam.py serve --port 8765`) for endpoint-connected follow-up work

## What works today

- **Original dashboard shell** - IDE layout, file explorer, code editor, runtime health bars, graphs, settings overlay, terminal, command menu, and agent chat
- **Prototype static serving** - Vite serves `prototype-backup/` as static content and frames `seam-dashboard-prototype.html` at the app root
- **REST panes** - the TypeScript endpoint panes remain in `src/panes/` as rework material, but they are no longer the root UI until they preserve the original shell

## Design

- Preserves the IDE-like shell from the original prototype as the first screen
- Dark theme with JetBrains Mono typography
- Activity bar on the left, main pane on the right, status bar at the bottom
- UI states: disconnected, unauthorized, loading, success, error

## Notes

- The prototype backup lives in `experimental/webui/prototype-backup/`
- The regression/restoration record lives in `experimental/webui/RESTORE_NOTES.md`
- Keep secrets local; tokens are never committed
- This remains experimental until it has repeatable browser smoke tests
