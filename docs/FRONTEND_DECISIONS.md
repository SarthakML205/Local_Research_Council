# FRONTEND_DECISIONS.md — Living Frontend Architecture Decision Records (ADR)

| ADR ID | Date | Scope | Title | Measured Impact |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-F01** | 2026-10-21 | Mind Map / Graph | Force-Directed SVG Canvas & Modular 8-Tile HUD | 60 FPS rendering on Apple Silicon; zero heavy canvas DOM leaks; modular 8-tile extraction inspection. |
| **ADR-F02** | 2026-10-21 | Debate / Real-time | Multi-Pane Virtual Advocate Chamber & SSE Bus | Zero-drop live token streaming; real-time token budget meter; auto-scrolling debate transcript. |
| **ADR-F03** | 2026-10-21 | Telemetry / Audit | 1-Second Reactive Physics Watchdog & Sovereign LED | Sub-millisecond UI state updates; live Unified RAM warning/ceiling meters; zero external network egress. |
| **ADR-F04** | 2026-10-22 | Design System / Theme | Stark UI 26 Minimalist Sci-Fi Mechanical Design Tokens | Void-black `#030405` shell, stippled grid, `.plate` red ticks, corner brackets; 0 console errors. |
| **ADR-F05** | 2026-10-22 | Carousel / Bookshelf | 3D Revolving Card Shelf & Tabular `#panel` Inspector | 3D perspective fan with 430px spacing; 0 collision; instant scrubber and category filtering. |
| **ADR-F06** | 2026-10-22 | Navigation / Shell | 260px Vertical Command Sidebar & M5 Hardware Telemetry | Unified navigation across 6 modules; real-time memory meter and live BKK clock. |
| **ADR-F07** | 2026-10-22 | Chamber / Podiums | Permanent Sovereign Dais & 4-Advocate Podiums with Dialectic Controls | Dais & podiums permanently visible; auto-staging debate runs; live token SLA held at 585/2048. |

---

## ADR-F01: Force-Directed Sci-Fi Mind Map & Modular 8-Tile HUD

### Context
Research paper mind maps must visually represent multi-tiered knowledge graphs (paper nodes, prerequisite study topics, and adjacent fields) with typed edges (`extends`, `contradicts`, `prerequisite_for`). Clicking a node must inspect detailed paper extractions without cluttering the screen or inducing canvas layout reflows.

### Decision
Implement a pure reactive SVG and CSS force-directed graph canvas with:
- Dark-mode glassmorphic aesthetic (`backdrop-filter: blur(12px)`).
- Glowing typed SVG curved bezier edges with directional arrow markers and color coding.
- Responsive side-drawer / split-panel displaying the 8-Tile Modular HUD (TLDR, Core Thesis, Methodology, Quantitative Results, Significance, Abstract, Admitted Gaps, Next Steps).

---

## ADR-F02: Real-Time Multi-Agent Chamber & SSE Event Stream

### Context
In multi-agent debates, users need to follow live dialogue turns, active speakers, position card summaries, and strict prompt token budgets in real time.

### Decision
- Event streaming via native browser `EventSource` connected to `/api/stream/events`.
- Responsive layout supporting 2 to 6 virtual advocates + 1 Moderator.
- Interactive controls: `Step Turn`, `Auto-Run Debate`, and `Synthesize Mind Map`.
- Color-coded speaker avatars and live token meter displaying:
  `System: 256 | RAG: 1,024 | History: 768 | Total: <= 2,048 Tokens`.

---

## ADR-F03: Hardware Telemetry Dashboard & Sovereign Health LED

### Context
Apple M5 24 GB hardware constraints require real-time visibility into process RSS, Metal GPU buffers, and latency percentiles (p50, p95, p99) to verify zero cloud egress and hardware physics safety.

### Decision
- Live LED indicator in top navigation shell: Green (healthy), Amber (>= 16 GB warning), Red (>= 18 GB ceiling).
- Telemetry dashboard with Unified Memory gauges, token velocity indicators, and typed failure logs.

---

## ADR-F04: Stark UI 26 Minimalist Sci-Fi Mechanical Design Tokens

### Context
Standard dark-mode web designs often look generic, flat, or inconsistent with washed-out light bleeding around browser edges. The user required a high-density, futuristic aesthetic inspired by Augma Imaginarium (Stark UI 26).

### Decision
Establish explicit CSS custom properties and mechanical plate styling in `app/frontend/src/index.css`:
- **Color Tokens:** Void-black (`#030405`), glowing Stark red (`#c8102e`), hairline borders (`rgba(200, 214, 226, 0.22)`), and neon cyan accents (`#5aa9dc`).
- **Mechanical Plates:** `.plate` containers with red 14px top-left tick mark and hairline top-right tick mark.
- **Corner Brackets:** `.chip` and `.btn-stark` elements carrying mechanical `L` and `⅃` corner notches.
- **Typography:** Google Fonts `Rajdhani` (display/headers) and `Share Tech Mono` (telemetry/data).
- **Global Reset:** Explicitly bound `html, body, #root` to `#030405` with background stippled cross-hairs to eliminate all browser-default white margins and glow artifacts.

---

## ADR-F05: 3D Revolving Card Shelf (`ShelfView.jsx`)

### Context
Viewing research papers in a flat grid lacks spatial immersion and makes quick cross-paper comparison tedious.

### Decision
Implement a 3D revolving carousel view with:
- 3D perspective fan (`perspective: 1200px`, `transform: translateX(offset * 430px) translateZ(...) rotateY(offset * -28deg)`).
- Safe fallback string handling for paper summaries, preventing `"undefined..."` artifacts.
- Animated 2D canvas Möbius particle loop on the active center card.
- Scrubber and category chips (`ALL`, `CS.LG`, `CS.AI`, `CS.CL`, `CS.DC`).
- Floating `#panel` tabular inspector at the bottom with quick actions (`STAGED IN TRAY`, `CONVENE COUNCIL`, `ARXIV`).

---

## ADR-F06: 260px Vertical Command Sidebar Navigation (`Navigation.jsx`)

### Context
A horizontal navbar consumes valuable vertical space needed for debate speech bubbles and 3D carousels, while failing to provide a clear hierarchical overview of the sovereign copilot's modules.

### Decision
Replace top navigation with a 260px vertical command sidebar:
- Top Stark Brand Plate: `LRC REPO 04 // OPERATOR CONSOLE`.
- 6 Option Chips: `01 INQUIRY LAUNCHER`, `02 3D ROTATING SHELF`, `03 OPERATOR MIND MAP`, `04 DEBATE COUNCIL`, `05 LIBRARY ARCHIVE`, `06 HARDWARE M5 HUD`.
- Bottom Apple Silicon M5 telemetry card with live memory bar and real-time clock.

---

## ADR-F07: Permanent Sovereign Dais & 4-Advocate Podiums with Dialectic Controls

### Context
Hiding the council chamber when a debate was unlaunched or completed gave the impression of an empty or broken interface, and left buttons disabled with no way to start a new debate.

### Decision
Refactor `CouncilView.jsx` to permanently display the sovereign assembly:
- **Chancellor Dais:** Top center podium for `J.A.R.V.I.S. [CHANCELLOR & CONSENSUS ARBITER]`.
- **4-Advocate Array:** Responsive grid (`repeat(auto-fit, minmax(200px, 1fr))`) showing `F.R.I.D.A.Y.`, `E.D.I.T.H.`, `K.A.R.E.N.`, and `J.O.C.A.S.T.A.` with two-line title clamping and `DEFENDING` / `SPEAKING` badges.
- **Dialectic Controls:** `RE-CONVENE`, `STEP TURN`, and `NEW DEBATE RUN` buttons that auto-stage if unlaunched and allow on-demand re-runs.

---

## ADR-F08: Stark UI 26 Mechanical Drag-and-Drop PDF Upload Console

### Context
Users researching proprietary or local research papers need a direct, friction-free way to upload PDF files right from the inquiry launcher (Screen 1) without requiring command-line copying or navigating to secondary folders.

### Decision
Implement a dual-mode query launcher in `app/frontend/src/components/NewSessionView.jsx`:
- **Segmented Control:** `01 // arXiv Sovereign Query` vs `02 // Direct Local PDF Upload`.
- **Mechanical Dropzone:** Styled in Stark UI 26 `.plate` aesthetics with obsidian dark backdrop (`rgba(8, 12, 18, 0.75)`), dashed border, and amber corner registration marks.
- **Multi-File Staging:** Displays staged PDFs in a responsive grid showing filename, formatted file size (`KB` / `MB`), `.pdf` badge, and one-click removal (`X`).
- **Unified Actions:** Supports "Upload to Library Only" (stages to 3D shelf) and "Ingest & Convene Council" (stages directly to active Council Tray and enables immediate debate execution).
- **Multi-Destination Completion Buttons:** Once ingestion completes, provides instant navigation to "Enter Council Chamber", "Inspect in 3D Shelf", or "Explore Mind Map".

