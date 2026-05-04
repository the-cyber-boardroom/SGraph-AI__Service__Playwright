# Debrief — CI fix: pin Playwright base image tag

- **Date:** 2026-04-16
- **Commit:** `f219b01` — `ci: pin Playwright base image to v1.58.0-noble (v1.58.2 not published)`
- **Brief sections:** stack table in `.claude/CLAUDE.md`

## What was delivered

- Changed `FROM mcr.microsoft.com/playwright/python:v1.58.2-noble` → `FROM mcr.microsoft.com/playwright/python:v1.58.0-noble` in `sgraph_ai_service_playwright/docker/images/sgraph_ai_service_playwright/dockerfile`.

## Deviations from brief

- Brief + CLAUDE.md listed `v1.58.2-noble`. That tag does not exist on MCR. Latest published noble tag at time of writing is `v1.58.0-noble`. Dockerfile comment documents this.
- CLAUDE.md has NOT been updated to match; doing so is a future housekeeping item.

## Issues / bugs hit

- Screenshot from user: `mcr.microsoft.com/playwright/python:v1.58.2-noble: not found`.
- Confirmed via MCR tags API that `v1.58.2-noble` is not published.

## Lessons

- Always verify container image tags exist on the registry before pinning. Microsoft only ships point-release tags for specific Playwright versions, not every patch.
- When the spec disagrees with reality, reality wins — note the deviation in the Dockerfile and file a follow-up to update the spec.

## Follow-up

- Update CLAUDE.md stack table to reference `v1.58.0-noble` (or whichever is current when the next refresh happens). Capture as an observation so CLAUDE.md is brought in line when the librarian next runs.
