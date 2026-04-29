# Phase C — Strip the Playwright EC2 (9 containers → 2)

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__03__strip-playwright-ec2.md`.
**Predecessor:** Phase B step 7h — `sp vnc` complete (`41120fc`).

---

## What shipped

The Playwright EC2 now hosts only **2 containers**: `playwright` + `agent-mitmproxy`. Everything else moved to its sister section:

| Container | Was | Now lives in |
|---|---|---|
| `browser` (linuxserver/chromium, KasmVNC) | `COMPOSE_SVC_BROWSER` (provision_ec2.py:220) | `sp vnc` |
| `browser-proxy` (nginx for VNC) | `COMPOSE_SVC_BROWSER_PROXY` (:241) | `sp vnc` |
| `cadvisor` | `COMPOSE_SVC_CADVISOR` (:257) | `sp prom` |
| `node-exporter` | `COMPOSE_SVC_NODE_EXPORTER` (:271) | `sp prom` |
| `prometheus` | `COMPOSE_SVC_PROMETHEUS` (:288) | `sp prom` |
| `fluent-bit` | `COMPOSE_SVC_FLUENT_BIT` (:305) | `sp os` (deferred — fluent-bit fragment not yet on `sp os`) |
| `dockge` | `COMPOSE_SVC_DOCKGE` (:318) | **deleted** (operator UI; no sister section needs it) |

## What got deleted

| File | Lines removed |
|---|---|
| `scripts/provision_ec2.py` | -216 (compose constants + templates + render functions) |
| `scripts/provision_ec2.py` | additional cleanup in `render_compose_yaml` / `render_user_data` / `provision()` |

Concretely:

- 7 compose-fragment constants: `COMPOSE_SVC_BROWSER`, `COMPOSE_SVC_BROWSER_PROXY`, `COMPOSE_SVC_CADVISOR`, `COMPOSE_SVC_NODE_EXPORTER`, `COMPOSE_SVC_PROMETHEUS`, `COMPOSE_SVC_FLUENT_BIT`, `COMPOSE_SVC_DOCKGE`.
- 7 config-template constants: `PROMETHEUS_YML_TEMPLATE`, `PROMETHEUS_REMOTE_WRITE_TEMPLATE`, `FLUENT_BIT_PARSERS_CUSTOM`, `FLUENT_BIT_LUA_CONTAINER_NAME`, `FLUENT_BIT_CONF_TEMPLATE`, `FLUENT_BIT_OUTPUT_OPENSEARCH`, `FLUENT_BIT_OUTPUT_STDOUT`, `NGINX_BROWSER_CONF_TEMPLATE`.
- 2 render functions: `render_observability_configs_section`, `render_browser_proxy_section`.
- `prometheus_data` named volume (the only volume that ever made it into code; `grafana_data` and `loki_data` mentioned in the v0.1.31 reality doc never landed).
- `render_compose_yaml` function: dropped `amp_remote_write_url`, `opensearch_endpoint` params + the 3 conditional branches + the DOCKGE service line + the volume rendering. Now ~25 lines.
- `render_user_data` function: dropped `amp_remote_write_url`, `opensearch_endpoint`, `upstream_url` params + the obs/browser-proxy/browser-pull/dockge substitutions. Now ~12 lines.
- `provision()` function: dropped the `AMP_REMOTE_WRITE_URL` / `OPENSEARCH_ENDPOINT` env reads + the `obs_section` + `browser_image_pull_ami` rendering.
- `USER_DATA_TEMPLATE` and `AMI_USER_DATA_TEMPLATE`: dropped `{browser_image_pull}`, `docker pull {dockge_image}`, `{observability_configs_section}`, `{browser_proxy_section}` placeholders + `mkdir /opt/dockge/data`.

## SG ports

`Ec2__AWS__Client.SG_INGRESS_PORTS` shrank from 3 ports → 2:

```python
SG_INGRESS_PORTS = (EC2__PLAYWRIGHT_PORT, EC2__SIDECAR_ADMIN_PORT)   # 8000 + 8001
```

`EC2__BROWSER_INTERNAL_PORT = 3000` is **kept** as a module constant — it's still referenced by `sp open` (line 2774) and `sp forward-browser` (line 2830). Those typer commands get deleted in Phase D, at which point the constant goes too.

`SG__DESCRIPTION` updated to reflect the 2-port shape (browser-VNC mention removed).

## What's NOT in this commit

Per plan doc 7 (Phase D), the following stay until command cleanup:

- `sp forward-prometheus` / `sp forward-browser` / `sp forward-dockge` typer commands — broken transitionally (their target containers are gone) but still registered. **Phase D deletes them.**
- `sp open` URL hints (lines 2774-2776) reference `localhost:3000` / `localhost:5001` / `localhost:9090` — broken transitionally. **Phase D updates these to point at `sp vnc connect` / `sp prom forward` / etc.**
- `sp diagnose` port-grep filter (line ~2143) lists `5001|9090|3000` — harmless (they just won't match any listener).
- `IAM__PROMETHEUS_RW_POLICY_ARN` / `IAM__OBSERVABILITY_POLICY_ARNS` — still present in `Ec2__AWS__Client`. Removing them risks breaking the IAM helper signatures. Their effect (allow remote-write to AMP) is now irrelevant since Prometheus isn't on this EC2 anymore; safe to leave.

## Tests

| Group | Change |
|---|---|
| `tests/unit/scripts/test_provision_ec2.py::test_render_compose_yaml` | Removed the `upstream_url='http://corp:3128'` kwarg from `test__api_key_in_both_services` (browser PASSWD count drops 3→2). Removed `test__upstream_vars_included` from being browser-coupled. `test__restart_always` count tightened to `== 2`. **New** `test__no_browser_or_observability_services` defensively checks none of the 6 stripped containers leak through. |
| `tests/unit/scripts/test_provision_ec2.py::test_render_observability_configs` | **Entire class deleted** (8 tests) — function it tested no longer exists. |
| `tests/unit/.../ec2/service/test_Ec2__AWS__Client.py::test_ensure_security_group__creates_when_missing` | Authorise-ingress call count 3 → 2. |
| `tests/unit/.../ec2/service/test_Ec2__AWS__Client.py::test__sg_ingress_ports_are_canonical` | Tuple shrinks to 2 ports; `EC2__BROWSER_INTERNAL_PORT` constant retained until Phase D drops `sp forward-browser`. |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/` + `tests/unit/scripts/` | ~990 | 997 | +7 (one defensive test added; 8 obs tests removed; 1 deduped) |

All 997 passing. Pre-existing flake in `lets/cf/inventory` excluded.

## Files changed

```
M  scripts/provision_ec2.py                                                          (~−270 net)
M  sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py                 (~−5 / +5 — SG_INGRESS_PORTS shrunk + comments updated)
M  tests/unit/scripts/test_provision_ec2.py                                          (~−65 — observability test class removed; assertions updated)
M  tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py (~+3 / −2)
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## What the EC2 boot does now

```bash
# UserData on a fresh AL2023 host:
dnf install -y docker
systemctl enable --now docker
# install docker compose plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl ... > /usr/local/lib/docker/cli-plugins/docker-compose; chmod +x ...
# ECR login + 2 image pulls
aws ecr get-login-password ... | docker login ...
docker pull <playwright-image>
docker pull <agent-mitmproxy-image>
docker logout; rm -f /root/.docker/config.json
# write compose + start
mkdir -p /opt/sg-playwright/config
cat > /opt/sg-playwright/docker-compose.yml << EOF ... EOF
docker compose -f /opt/sg-playwright/docker-compose.yml up -d
```

That's the whole boot. AMI size should drop from ~3 GB → ~1.2 GB the next time the bake-AMI flow runs (operator-driven; not part of this commit per plan).

## Failure classification

**Good failure** — none caught by tests because the strip is mostly deletion. The defensive `test__no_browser_or_observability_services` test (added in this commit) locks the new shape so any future "let me re-add a small thing" gets caught immediately.

## Next

**Phase D — command cleanup:**
- D.1 — Drop `sp forward-prometheus` / `sp forward-browser` / `sp forward-dockge` typer commands. Drop `EC2__BROWSER_INTERNAL_PORT` / `EC2__DOCKGE_PORT` / `EC2__DOCKGE_IMAGE` / `EC2__BROWSER_IMAGE` / `EC2__PROMETHEUS_PORT` constants once the last consumer is gone. Update `sp open` to point at `sp vnc connect` / `sp prom forward`.
- D.2 — Move `sp metrics <url>` → `sp prom metrics <url>` (per plan doc 7 C2).
- D.3 — Regroup `sp vault-*` flat commands under `sp vault` subgroup (per C1 hard cut).
- D.4 — Regroup `*-ami` flat commands under `sp ami` subgroup (matches `sp el ami` shape).
