# Observation — Playwright base image tag mismatch between spec and reality

- **Date captured:** 2026-04-16
- **Source:** Claude (self) — surfaced while fixing CI docker-build failure (`mcr.microsoft.com/playwright/python:v1.58.2-noble: not found`).
- **Status:** OPEN — `CLAUDE.md` stack table still says `v1.58.2-noble`. Dockerfile now pins `v1.58.0-noble`.

## Issue

`.claude/CLAUDE.md` lists the base image as `mcr.microsoft.com/playwright/python:v1.58.2-noble`. That tag does not exist on MCR. The latest published `noble` tag at time of writing is `v1.58.0-noble`, which the Dockerfile now uses.

## Recommendation

When the librarian next runs a pass over the stack doc:

- Update the CLAUDE.md stack table Base image row to match whatever is pinned in the Dockerfile.
- Add a CI job or pre-commit check that verifies the Dockerfile's `FROM` tag exists on the registry. One approach: a small pytest that `HEAD`s the MCR manifest URL.

## Lesson (rolled into `debriefs/2026-04-16__ci-fix-playwright-tag.md`)

Always verify container tags on the registry before pinning. Specs drift faster than publishers ship.
