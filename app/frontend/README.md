# LRC Sovereign Frontend — Stark UI 26 Operator Console

> Minimalist Sci-Fi Research Interface inspired by Augma Imaginarium (Stark UI 26) running 100% locally on Apple Silicon.

---

## 1. Design System & Aesthetics

The frontend uses pure Vanilla CSS tokens, glassmorphism, and mechanical plate geometry:
- **Background:** Void-black (`#000000` / `#030405`) with stippled SVG cross-hair background grid (`+`).
- **Accents:** Stark Red (`#c8102e`), Sovereign Cyan (`#38bdf8`), and M5 Emerald (`#10b981`).
- **Geometry:**
  - `.plate`: Containers featuring a red 14px top-left tick mark and hairline top-right tick mark.
  - `.chip` & `.btn-stark`: Corner bracket notches (`L` and `⅃`) with hover transitions.
  - `.hud-bar`: Floating tabular inspector status bar displaying node IDC badge, type, stack, and real-time clock.
- **Typography:** Google Fonts:
  - `Rajdhani` (display/headers, letter-spacing -0.01em)
  - `Share Tech Mono` (telemetry, coordinates, and code)
  - `JetBrains Mono` (fallbacks)

---

## 2. Views & Component Architecture

| View Component | Route Tab | Description |
| :--- | :--- | :--- |
| `Navigation.jsx` | Sidebar | 260px vertical command sidebar with brand plate, 6 option chips, live M5 memory meter, and clock. |
| `NewSessionView.jsx` | `01 INQUIRY LAUNCHER` | Research query input, arXiv scraper trigger, and 3-way strategy comparison benchmark HUD. |
| `ShelfView.jsx` | `02 3D ROTATING SHELF` | 3D revolving carousel with perspective fan, particle mesh canvas, category filters, and `#panel` inspector. |
| `DiscoveryView.jsx` | `03 OPERATOR MIND MAP` | Force-directed SVG relational graph with typed bezier edges (`extends`, `contradicts`, `prerequisite_for`) and 8-tile drawer. |
| `CouncilView.jsx` | `04 DEBATE COUNCIL` | Chamber Dais (`J.A.R.V.I.S.`), permanent 4-advocate podium array, live speech stream, token budget meter, and consensus synthesis. |
| `LibraryView.jsx` | `05 LIBRARY ARCHIVE` | Sovereign paper bookshelf, inbox directory scanner, arXiv downloader, and Council Tray staging. |
| `DashboardView.jsx` | `06 HARDWARE M5 HUD` | Apple Silicon M5 RSS/Metal memory gauges, p50/p95/p99 latency cards, zero-token audit ledger, and typed failure log. |

---

## 3. Local Development

```bash
# Start local Vite development server on port 5173
npm run dev -- --host 127.0.0.1 --port 5173

# Build production bundle
npm run build

# Preview production build
npm run preview
```
