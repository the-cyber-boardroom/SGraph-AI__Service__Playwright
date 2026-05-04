# v0.1.118 — Caddy swap & ongoing CLI / FastAPI handover

**Author:** Claude (Opus 4.7) — handover written 2026-04-29
**For:** Claude Code Sonnet — picking up the thread

This handover bundles the working knowledge from a long debugging-and-build
session that ended with the nginx → Caddy swap on `sp vnc`. The next
session is expected to keep iterating on the **CLI**, the **base classes**
(`Type_Safe`-based building blocks under `sgraph_ai_service_playwright__cli/`),
and the **FastAPI** routes that mirror the CLI commands.

## Files in this handover

| File | What's in it |
|------|--------------|
| `01__where-we-are.md` | Current branch, last commit, what works end-to-end, what's still rough |
| `02__open-threads.md` | Concrete follow-up slices, ranked by urgency |
| `03__codebase-map.md` | Key files for CLI, base classes, FastAPI — where to start when a task lands |
| `04__resumption-prompt.md` | **Copy-paste prompt** to kick off the new session |

## TL;DR for the human

- **Branch:** `claude/refactor-playwright-stack-split-Zo3Ju` (multiple agents have been working on this branch — keep merging from `origin/dev`).
- **Just landed:** `b9123d1` — `sp vnc` now boots Caddy + caddy-security in place of nginx + Basic auth. End-to-end tested: `sp vnc create --password 1234 --wait --open` produces a stack where `https://{ip}/` redirects to a Caddy login page.
- **Default behaviour you should preserve:** `sp` CLI subgroups (`sp linux`, `sp docker_stack`, `sp prom`, `sp os`, `sp vnc`, `sp el`, `sp pw`, `sp catalog`, `sp doctor`) all use the same Tier-1 / Tier-2A / Tier-2B pattern; routes never have business logic; `_Fake_*` classes (NOT `unittest.mock`) for tests.

## Read in this order before writing code

1. `.claude/CLAUDE.md` — project rules (it's pulled into every session automatically, but read it consciously).
2. `library/catalogue/README.md` — fractal index of packages, services, tests, AWS resources.
3. The current reality doc under `team/roles/librarian/reality/` (filename is version-stamped — README points at the latest).
4. This handover folder, then `04__resumption-prompt.md`.
5. The role definition that matches your task: `team/roles/dev/ROLE.md` for implementation, `team/roles/architect/ROLE.md` for schema/route changes.

Then write code.
