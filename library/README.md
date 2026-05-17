# Library

**In-repo knowledge base for the SG Playwright Service.**

Until 2026-04-17 the authoritative specs lived only in an sgit vault; this directory brings that content into the repo so every agent can read it without credentials. The vault remains the upstream source for cross-repo dev packs, but anything relevant to this service is mirrored here and version-stamped.

---

## Directory Map

| Path | Purpose |
|------|---------|
| [`docs/specs/`](docs/specs/)         | **Definitive** specifications — schema catalogue, routes catalogue, CI pipeline |
| [`docs/research/`](docs/research/)   | Background investigations (base image, prior art, OSBot-Playwright deep dive) |
| [`docs/_to_process/`](docs/_to_process/) | Inbox for unsorted material — Librarian classifies and moves out |
| [`guides/`](guides/)                 | Framework guides (Type_Safe, Safe primitives, testing, FastAPI routes, etc.) |
| [`roadmap/phases/`](roadmap/phases/) | Phased delivery plan (Phase 0 → Phase 4) |
| [`onboarding/`](onboarding/)             | Orientation documents — what the project is, reading order, first-session prompt |
| [`reference/`](reference/)           | Architecture brief + decisions log (historical context) |
| [`dev_packs/`](dev_packs/)           | Briefing packs for downstream agent sessions (placeholder) |
| [`skills/`](skills/)                 | Reusable skill packs (placeholder) |

---

## Reading Order for a New Agent

1. [`onboarding/v0.20.55__07_first-session-brief.md`](onboarding/v0.20.55__07_first-session-brief.md) — start here
2. [`onboarding/v0.20.55__01_project-context.md`](onboarding/v0.20.55__01_project-context.md) — what the service is, 5 deployment targets
3. [`onboarding/v0.20.55__02_mission-brief.md`](onboarding/v0.20.55__02_mission-brief.md) — phased deliverables + rules
4. [`onboarding/v0.20.55__04_practices-reference.md`](onboarding/v0.20.55__04_practices-reference.md) — Type_Safe quick rules
5. [`guides/v3.63.4__type_safe.md`](guides/v3.63.4__type_safe.md) — **MUST READ** before writing any class
6. [`docs/specs/v0.20.55__schema-catalogue-v2.md`](docs/specs/v0.20.55__schema-catalogue-v2.md) — definitive schema spec
7. [`docs/specs/v0.20.55__routes-catalogue-v2.md`](docs/specs/v0.20.55__routes-catalogue-v2.md) — definitive routes + service classes
8. [`docs/specs/v0.20.55__ci-pipeline.md`](docs/specs/v0.20.55__ci-pipeline.md) — CI + Docker + deploy-via-pytest

Before asserting what the service can do, cross-check against the **Reality Document** at [`../team/roles/librarian/reality/`](../team/roles/librarian/reality/).

---

## Naming Convention

Every file under `library/` carries a version prefix: `{version}__{description}.md`.

- Dev-pack content keeps the pack's own version (`v0.20.55`).
- Framework guides keep the version of the upstream library they describe (`v3.63.4__type_safe.md` documents Type_Safe as shipped in `osbot-utils` 3.63.4).
- New content authored here uses the current service version from `sgraph_ai_service_playwright/version`.
