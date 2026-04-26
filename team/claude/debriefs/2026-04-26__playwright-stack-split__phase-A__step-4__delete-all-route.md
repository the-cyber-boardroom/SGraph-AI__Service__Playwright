# Phase A · Step 4 — `DELETE /ec2/playwright/delete-all` route

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/02__api-consolidation.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 3f (typer command reduction).

---

## Why

Doc 7 step 4 calls for "FastAPI routes for any EC2 op currently CLI-only". After the route survey:

- `list` / `info` / `create` / `create_named` / `delete` already had routes
- `delete --all` did NOT — it iterated locally inside the typer command
- Other typer commands (`connect`, `shell`, `exec`, `forward`, `wait`, `screenshot`, `smoke`, `bake-ami`, etc.) are interactive (SSM session, port-forwarding, screenshots) and don't fit stateless HTTP

Step 3f already added `Ec2__Service.delete_all_instances()`. This slice exposes it as the matching route.

## What shipped

**New route:**
- `DELETE /ec2/playwright/delete-all` → `Routes__Ec2__Playwright.delete_all()` → `service.delete_all_instances()` → `Schema__Ec2__Delete__Response`. Empty `target` / `deploy_name`; populated `terminated_instance_ids`.

**In-memory test fixture extended:**
- `Ec2__Service__In_Memory.delete_all_instances()` — dedups the fixture map (which carries both deploy-name AND instance-id keys for the same Schema) and returns the matching response shape.

**One new route test** in `test_Fast_API__SP__CLI.py::test_delete_all` — exercises the route end-to-end via FastAPI's TestClient against the in-memory service (no mocks).

## Test outcome

| Suite | Before (3f) | After (4) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1174 passed | 1176 passed | +2 |

Same 1 unchanged pre-existing failure.

## What was not added (and why)

The other typer commands without routes:

| Command | Why not |
|---|---|
| `connect`, `shell` | Interactive SSM sessions — no request/response shape |
| `exec`, `exec-c` | Could be a route (`POST /ec2/playwright/exec` with body) but each exec call needs streaming output — out of scope for this plan |
| `forward`, `forward-prometheus`, `forward-browser`, `forward-dockge` | Local port forwarding — client-side, not server-side |
| `screenshot`, `smoke`, `health` | These call the live Playwright EC2 across the network. They could become routes that proxy/aggregate, but that's a different concern (observability tooling, not stack lifecycle) |
| `wait` | Polling helper; better as a polled status route than a long-poll endpoint |
| `bake-ami`, `wait-ami`, `tag-ami`, `list-amis`, `create-from-ami` | AMI lifecycle — should land under a dedicated `Routes__Ec2__Ami` module when AMI ops are needed via API. Out of scope for step 4. |
| `vault-*` | Vault interactions — separate concern from EC2 lifecycle |
| `ensure-passrole` | Already has `Routes__CI__User__Passrole` (different module) |
| `clean`, `diagnose`, `logs`, `env`, `open`, `metrics` | Diagnostic / informational; route equivalents not blocking. |

## Phase A — DONE

| Step | Status |
|---|---|
| 1 — `Stack__Naming` (shared helper) | ✅ |
| 2 — `Image__Build__Service` (shared docker-build) | ✅ |
| 3a — Naming + lookup helpers | ✅ |
| 3b — AWS context accessors | ✅ |
| 3c — IAM helpers | ✅ |
| 3d — SG + AMI helpers | ✅ |
| 3f — Typer wrappers for `list`/`info`/`delete` | ✅ |
| 4 — `delete-all` route | ✅ |

Phase A's foundation work is complete:
- Shared `cli/aws/Stack__Naming` (docs 1, 2 unblocked)
- Shared `cli/image/Image__Build__Service` (sister sections inherit a Docker-build pipeline for free)
- Comprehensive `cli/ec2/service/Ec2__AWS__Client` (single AWS boundary)
- `Ec2__Service` no longer needs lazy `from scripts.provision_ec2 import` for EC2 lookup, AWS context, or AMI lifecycle
- Three core typer commands (`list`/`info`/`delete`) reduced to thin wrappers over the service
- `delete --all` available as both CLI and HTTP

What remains in `provision_ec2.py`:
- Userdata + compose rendering (~600 lines) — gets dramatically simplified by Phase C strip; deferred there
- 12 typer commands still using `_resolve_target` — mechanical reduction; can land alongside Phase C or in a follow-up
- `_print_auth_error` and `_print_preflight_*` Tier-2A formatters — appropriately placed

## Files changed

```
M  sgraph_ai_service_playwright__cli/fast_api/routes/Routes__Ec2__Playwright.py
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service__In_Memory.py
M  tests/unit/sgraph_ai_service_playwright__cli/fast_api/test_Fast_API__SP__CLI.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Phase B — start carving out the sister sections (`sp os` first, since it's the cleanest licensing-wise per doc 8 and the OpenSearch images are stable). Phase A's `Ec2__AWS__Client` + `Stack__Naming` + `Image__Build__Service` are the building blocks each new section will reuse.
