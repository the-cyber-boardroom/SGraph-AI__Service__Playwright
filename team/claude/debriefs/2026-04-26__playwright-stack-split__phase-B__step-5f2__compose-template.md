# Phase B · Step 5f.2 — `OpenSearch__Compose__Template`

**Date:** 2026-04-26.
**Commit:** `8658520`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5f.1 (user-data skeleton).

---

## What shipped

`OpenSearch__Compose__Template.py` (~70 lines) — single-purpose `docker-compose.yml` renderer for single-node OpenSearch + Dashboards.

| Field | Value |
|---|---|
| `OS_IMAGE` | `opensearchproject/opensearch:latest` (per plan doc 4 OS1: moving tag in production) |
| `DASHBOARDS_IMAGE` | `opensearchproject/opensearch-dashboards:latest` |
| `COMPOSE_TEMPLATE` | YAML with single `opensearch` + `dashboards` services on `sg-net` network |
| `PLACEHOLDERS` | `(os_image, dashboards_image, admin_password, heap_size)` — locked by test |
| `.render(admin_password, heap_size='2g', os_image=..., dashboards_image=...)` | returns the YAML string; tests can override images for pinning |

Compose invariants (locked by test):
- `bootstrap.memory_lock=true` + `memlock` ulimits (required for OS 2.x)
- Container names `sg-opensearch` + `sg-opensearch-dashboards` (sp os exec / connect target these)
- Shared `sg-net` bridge network (matches playwright stack convention)
- Dashboards `depends_on: [opensearch]` (Dashboards crashes if OS unreachable on boot)
- Named volume `opensearch-data` for persistence

## Tests

9 new tests:
- Default + custom heap substituted
- Custom image override (pinning) works
- No leftover `{key}` in output
- Canonical container names present
- `sg-net` defined + referenced
- `bootstrap.memory_lock` + `memlock` ulimits
- `depends_on` opensearch
- `PLACEHOLDERS` constant matches every `{key}` in template

## Failure classification

Type: **good failure**. The OS-2.x-specific invariants (memlock + memory_lock) are explicit tests so a future "lighter" template can't accidentally drop them and silently break boot.

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Compose__Template.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Compose__Template.py
```
