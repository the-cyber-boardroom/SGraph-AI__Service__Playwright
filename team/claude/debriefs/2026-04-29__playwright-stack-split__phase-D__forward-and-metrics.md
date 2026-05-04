# Phase D (1/2) — Drop forward-* / metrics + add `sp prom metrics <url>`

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__07__command-cleanup-and-migration.md`.
**Predecessor:** Phase C — strip Playwright EC2 (`9af6498`).

---

## What shipped

Per plan doc 7 (C1 hard cut + C2 metrics move), drop the orphaned typer commands whose targets moved out of the Playwright EC2 in Phase C, and replace `sp metrics` with the URL-based `sp prom metrics`.

| Command | Before | After |
|---|---|---|
| `sp forward-prometheus` | SSM-forwarded port 9090 | **deleted** (Prometheus moved to `sp prom`) |
| `sp forward-browser` | SSM-forwarded port 3000 | **deleted** (chromium-VNC moved to `sp vnc`) |
| `sp forward-dockge` | SSM-forwarded port 5001 | **deleted** (Dockge dropped entirely) |
| `sp metrics <service> --target <name>` | SSM-curled `/metrics` from playwright/sidecar | **deleted** (one-off; operators can use `sp exec ... curl ...`) |
| **NEW:** `sp prom metrics <url>` | — | URL-based fetch of any `/metrics` endpoint (`--key <api-key>` optional) |

## Constants dropped

`Ec2__AWS__Client.EC2__BROWSER_INTERNAL_PORT` (3000) — last consumer (`sp open` URL hint + `sp diagnose` port-grep + `sp forward-browser`) all gone in this commit. Test reference removed.

`scripts/provision_ec2.py`:
- `EC2__PROMETHEUS_PORT` (9090)
- `EC2__BROWSER_IMAGE` (`lscr.io/linuxserver/chromium:latest`)
- `EC2__DOCKGE_PORT` (5001)
- `EC2__DOCKGE_IMAGE` (`louislam/dockge:1`)

## Cleanup of stale UI references

| Where | Change |
|---|---|
| `sp open` URL-hint block | Dropped 3 lines (Browser / Dockge / Prometheus). Replaced with a one-line comment pointing at `sp vnc connect` / `sp prom forward`. |
| `sp diagnose` listening-ports grep | Filter shrunk from `8000\|8001\|5001\|9090\|3000\|5601` → `8000\|8001`. |
| `sp diagnose` port_rows table | Browser-VNC row dropped (was conditionally inserted when `upstream_url` was set). |
| `provision()` return dict | `browser_url` field removed (always `None` after Phase C). |
| `Ec2__Service.get_instance_info` | `browser_url` set to empty string (schema field retained for backwards compatibility). |

## `sp prom metrics <url>` shape

```
sp prom metrics <url>             [--key <api-key>] [--timeout <seconds>]
```

Fetches Prometheus exposition text from any URL via plain HTTP (no SSM, no AWS). Optional `X-API-Key` header. 30 s timeout default. Exits 1 on network failure or non-200.

This is the URL-based replacement promised in plan doc 5 P3 — works for any `/metrics` endpoint, not just the Playwright EC2.

## Tests

- `test__sg_ingress_ports_are_canonical` (in `cli/ec2/service/test_Ec2__AWS__Client.py`) — dropped the `EC2__BROWSER_INTERNAL_PORT` assertion (constant gone). Import block trimmed to match.
- All other tests pass unchanged. Note: `test_cli_surface::test__app_has_expected_commands` already does NOT include `forward-prometheus` / `forward-browser` / `forward-dockge` / `metrics` — so no test update needed there.

## Test outcome

| Suite | Before | After |
|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/` + `tests/unit/scripts/` | 997 | 997 |

No regressions.

## Files changed

```
M  scripts/provision_ec2.py                                                        (~−170 LoC)
M  scripts/prometheus.py                                                           (~+25 — new metrics command)
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py               (~−2 — constant removed)
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service.py                   (~−2 / +2 — dropped import + browser_url empty)
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py (~−2)
```

## What's still ahead

- **D.3** — Regroup `sp vault-clone` / `vault-list` / `vault-run` / `vault-commit` / `vault-push` / `vault-pull` / `vault-status` (7 flat commands) under `sp vault` subgroup. Hard cut per C1 — flat aliases dropped.
- **D.4** — Regroup `sp bake-ami` / `wait-ami` / `tag-ami` / `list-amis` (4 flat commands) under `sp ami` subgroup. `sp create-from-ami` stays top-level (per plan doc 7 — different action: launch instance from AMI).
