# FRONTEND_DECISIONS.md — Living Frontend Architecture Decision Records (ADR)

| ADR ID | Date | Scope | Title | Measured Impact |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-F01** | 2026-10-21 | Mind Map / Graph | Force-Directed SVG Canvas & Modular 8-Tile HUD | 60 FPS rendering on Apple Silicon; zero heavy canvas DOM leaks; modular 8-tile extraction inspection. |
| **ADR-F02** | 2026-10-21 | Debate / Real-time | Multi-Pane Virtual Advocate Chamber & SSE Bus | Zero-drop live token streaming; real-time token budget meter; auto-scrolling debate transcript. |
| **ADR-F03** | 2026-10-21 | Telemetry / Audit | 1-Second Reactive Physics Watchdog & Sovereign LED | Sub-millisecond UI state updates; live Unified RAM warning/ceiling meters; zero external network egress. |

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
