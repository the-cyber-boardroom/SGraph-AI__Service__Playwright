# 07 — Remaining Phases (concrete next-up)

## Phase B step 6 — `sp prom` (foundation done; 7 slices remaining)

Smaller surface than `sp os`. Per plan doc 5: no Grafana (P1), ephemeral with no EBS + 24 h retention (P2), one-shot baked scrape targets (P3), moving `latest` tags (P4).

| Slice | Template ref | Notes |
|---|---|---|
| **6b** | `9a1e04e` | Schemas + collections. **Drop** `admin_password` (Prometheus has no built-in auth) and `dashboards_url` (no UI per P1). **Add** `Schema__Prom__Scrape__Target` for the baked target list. |
| **6c** | `f5dcde7` | 4 small AWS helpers — `Prometheus__SG__Helper`, `Prometheus__AMI__Helper`, `Prometheus__Instance__Helper`, `Prometheus__Tags__Builder` + `Prometheus__Launch__Helper`. SG ingress port: `9090` (Prometheus public) only. |
| **6d** | `05c0bb7` | HTTP base + probe. Probe endpoints: `GET /-/healthy` (200 → ready), `GET /api/v1/targets` (count + up state), `GET /api/v1/query?query={query}` (forwarded for the future `sp prom query` command). |
| **6e** | `82afd0e` | `Prometheus__Service` orchestrator. `health()` returns `Schema__Prom__Health` with `targets_total` / `targets_up` / scrape-status counts. |
| **6f.1–4** | `363341c` → `2b21126` | User-data + compose. **No Dashboards container** (P1). Compose has 3 services: `prometheus` + `cadvisor` + `node-exporter`. Compose template includes a baked `prometheus.yml` rendered from a list of `Schema__Prom__Scrape__Target` per P3. |
| **6g** | `aef4018` | `Routes__Prometheus__Stack` — 5 routes mirroring `sp os` shape. |
| **6h** | `6abf20b` | `scripts/prometheus.py` typer app + Renderers + mount via `add_typer` (`sp prom` + `sp prometheus`). |

## Phase B step 7 — `sp vnc` (not started; 9 slices)

Most complex sister section. Per plan doc 6: chromium-only at runtime (N2), profile + state wiped at termination (N3), no automatic flow export (N4), interceptor model is **default-off + ship examples + provision-time choice via env vars** (N5).

| Slice | Notes |
|---|---|
| **7a** | Foundation — `Safe_Str__Vnc__Stack__Name`, `Enum__Vnc__Stack__State`, `Vnc__AWS__Client` skeleton with `VNC_NAMING`. |
| **7b** | Schemas — Create/Response/Info/List/Delete/Health, plus `Schema__Vnc__Interceptor__Choice` (name | inline-source | none) per N5. |
| **7c** | 4 small AWS helpers (same shape as sp os/sp prom). SG ports: 443 (nginx TLS) + 3000 (KasmVNC SSM-forward only). |
| **7d** | HTTP base + probe. Probes `nginx /` 200 + mitmweb `/api/flows` reachable. |
| **7e** | Service orchestrator + Mapper + Caller__IP__Detector + Random__Name__Gen. |
| **7f** | User-data + compose. **3 containers**: `chromium` (linuxserver/chromium today; chromium-only image deferred per doc 5 P6), `nginx` (TLS terminator), `mitmproxy` (clone of agent_mitmproxy image with operator-debug interceptor). Per N5: bake example interceptors at `vnc/mitmproxy/interceptors/examples/`; resolve `--interceptor <name>` or `--interceptor-script <path>` at create time; default = no interceptor. |
| **7g** | `Routes__Vnc__Stack` + `Routes__Vnc__Flows` (mitmweb flow listing). |
| **7h** | `scripts/vnc.py` typer app — `sp vnc` only (no long alias `nginx-vnc-mitmproxy`); `sp vnc browser-viewer` would also work as a synonym. |

## Phase C — strip the Playwright EC2

Cannot ship until B6 + B7 give `sp prom` and `sp vnc` working compose fragments to host the moved containers.

| Sub-slice | Notes |
|---|---|
| **C.1** | Move `COMPOSE_SVC_BROWSER` + `COMPOSE_SVC_BROWSER_PROXY` to `sp vnc`; `COMPOSE_SVC_PROMETHEUS` + `COMPOSE_SVC_CADVISOR` + `COMPOSE_SVC_NODE_EXPORTER` to `sp prom`; `COMPOSE_SVC_FLUENT_BIT` to `sp os`. **No deletion yet** — duplicate while both work. |
| **C.2** | Delete the 3 `if` branches in `provision_ec2.py:967-979` + orphaned `COMPOSE_SVC_*` constants + `prometheus_data` volume. Update integration test container-count assertion from 9 to 2. |
| **C.3** | Drop ports 9090 / 3000 / 5001 / 8080 from the SG. Keep 8000 + 8001. Update SG description. |
| **C.4** | Drop `IAM__PROMETHEUS_RW_POLICY_ARN` from `IAM__OBSERVABILITY_POLICY_ARNS`. Confirm `sp prom` carries it. |
| **C.5** | Bake a new AMI; tag the previous as `superseded`. Document AMI size before/after (~3 GB → ~1.2 GB expected). |
| **C.6** | Update reality doc: `team/roles/librarian/reality/v0.1.31/03__docker-and-ci.md` 9-containers → 2-containers. Mark v0.1.31 observability extension as superseded. |

## Phase D — command cleanup

Per plan doc 7 sign-off (C1 hard-cut, C2 `sp metrics` → `sp prom metrics`):

| Action | Notes |
|---|---|
| Regroup `vault-*` flat top-level commands under `sp vault` subgroup. Drop the flat aliases (hard cut — C1). |
| Regroup `*-ami` flat top-level commands under `sp ami` subgroup. Verbs match `sp el ami {list, create, delete, wait}` (already shipped on dev). `sp ami create` (was `sp bake-ami`); `sp create-from-ami` stays at top level. |
| Delete `sp forward-prometheus`, `sp forward-browser`, `sp forward-dockge`. |
| Move `sp metrics <url>` to `sp prom metrics <url>` (C2). |
| Update `sp --help` documentation in operator runbook. |

## Deferred

- **5g** — Dashboard generator with shared `Base__Dashboard__Generator` extracted from `elastic`. Not blocking; touches both sections; best done as its own slice.
- **AMI lifecycle helpers** for `sp os` / `sp prom` / `sp vnc` (`{X}__AMI__Lifecycle__Helper.py` with `create_ami` / `wait_ami_available` / `tag_ami` / `deregister_ami`). Not needed until `sp os ami` / `sp prom ami` / `sp vnc ami` subcommands are wired.
- **OpenSearch dashboard auto-import** on `sp os create` — depends on 5g landing.
- **`sp prom add-target` dynamic flow** — deferred per plan doc 5 P3 (one-shot baked targets ship first).
- **Audit export of mitmproxy flows** on `sp vnc delete` — deferred per N4 (no external sink yet).

## Estimated remaining commits

If pacing matches this session: ~7 commits for `sp prom`, ~9 for `sp vnc`, ~6 for Phase C, ~4 for Phase D. **Roughly 25–30 more commits** to fully complete the v0.1.96 plan. Plan to land them across ~3-4 fresh sessions with similar discipline.
