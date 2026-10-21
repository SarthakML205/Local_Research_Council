---
trigger: always_on
---

---
trigger: always_on
description: "Enforces atomic git commits, conventional commit message formats, and mandatory verification gates before marking tasks complete."
---

# Git, Commit & Execution Workflow

1. **Atomic Commits:**
   - Make small, self-contained commits focused on a single module or test suite (e.g., `feat(core): implement immutable FSM state container with BLAKE2b hashes`).
2. **Conventional Commits with Metrics:**
   - Commit messages must follow the pattern: `<type>(<scope>): <short summary>`
   - Types: `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `chore`.
   - If a commit impacts performance or memory, include the measured metric in the commit body (e.g., `Measured p99 dispatch latency: 0.94ms under 100 concurrent tasks`).
3. **Never Force-Push to Main:**
   - Keep experimental or failing code in feature branches until all `pytest` verification gates pass cleanly.