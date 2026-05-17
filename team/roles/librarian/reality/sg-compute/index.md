# Reality — SG/Compute Domain

**Status:** ACTIVE — seeded in phase-1 (B1), foundations added in phase-2 (B2), pod management in BV2.3, CLI builder in v0.2.6, billing CLI in v0.2.22, vault-publish spec in v0.2.23.
**Last updated:** 2026-05-17 | **Phase:** v0.2.23 (vault-publish spec — subdomain routing cold path)

This is the cover sheet for the SG/Compute reality domain. Detailed per-subarea inventories live in the sub-files linked below. If a fact is not listed in one of those sub-files, it does not exist.

---

## Packages

| Package | Location | Description |
|---------|----------|-------------|
| `sg_compute` | `sg_compute/` | SDK — primitives, enums, core schemas, Platform interface, EC2 platform, Spec__Loader/Resolver/Registry, Node__Manager |
| `sg_compute_specs` | `sg_compute_specs/` | Spec catalogue — pilot specs (ollama, open_design, docker), plus the v0.2.23 `vault_publish` spec with its Waker Lambda |
| `sg_compute__tests` | `sg_compute__tests/` | Test suite — 152 tests, mirrors `sg_compute/` and `sg_compute_specs/` layout |

---

## Subareas

### Primitives, enums, and core schemas — [`primitives.md`](primitives.md)

The cross-cutting type vocabulary: `Safe_Str__*`, `Safe_Int__*`, `Enum__Spec__*`, `Enum__Node__State`, `Enum__Pod__State`, `Enum__Stack__Creation_Mode`. Also covers `sg_compute/core/node/`, `sg_compute/core/spec/` (registry/loader/resolver/UI+README resolvers), `sg_compute/core/event_bus/`, `sg_compute/catalog/enums/`, and `sg_compute/image/` (Docker image build orchestrator).

### Platform interface & EC2 — [`platform.md`](platform.md)

`Platform` abstract base, `EC2__Platform`, all `platforms/ec2/` helpers (`Launch__Helper`, `SG__Helper`, `Tags__Builder`, `AMI__Helper`, `Instance__Helper`, `Stack__Mapper`, `Stack__Naming`), user-data sections (`Section__Base/Docker/Node/Nginx/Env__File/Shutdown/Sidecar/GPU_Verify/Ollama/Claude_Launch/Agent_Tools`), `Health__Poller/HTTP__Probe`, networking helpers, EC2 primitives/enums/collections, and `Node__Manager`.

### Spec catalogue, manifests, and pilots — [`specs.md`](specs.md)

`sg_compute_specs/` pilot specs (`ollama`, `open_design`, `docker`), manifest typing, the `vault_publish` spec (slug registry, Waker Lambda, CloudFront + Lambda CRUD primitives), and the `sg_compute/vault/` package (write receipts, `Vault__Spec__Writer`, `/api/vault` routes).

### CLI surface — [`cli.md`](cli.md)

`sg_compute/cli/base/` (`Spec__CLI__Builder` v0.2.6, `Spec__Service__Base`, resolvers, errors, defaults, renderers, result schemas), the `sg aws billing` CLI sub-package (v0.2.22), and the `sg vp` vault-publish CLI (v0.2.23) along with its supporting `sg aws cf` and `sg aws lambda` primitives.

### Pod management — [`pods.md`](pods.md)

`sg_compute/core/pod/` (BV2.3 + T2.6b/T2.6c): pod schemas (`Schema__Pod__Info / List / Stats / Logs / Stop / Start__Request`), `Dict__Pod__Ports`, `Dict__Pod__Env`, `Sidecar__Client`, `Pod__Manager`. Also covers `sg_compute/control_plane/` (`Fast_API__Compute`, `Routes__Compute__*` including health/specs/nodes/pods/AMIs/stacks/legacy), `core/ami/`, and the api_site dashboard web components under `sg-compute/`.

### Host plane — [`host-plane.md`](host-plane.md)

Pointer to the `sg_compute/host_plane/` package. The host-control HTTP surface itself is documented in the sibling reality domain — see [`../host-control/index.md`](../host-control/index.md).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## History

| Date | Change |
|------|--------|
| 2026-05-17 | v0.2.23: vault-publish spec — full cold path: slug registry (SSM), `Vault_Publish__Service` (register/unpublish/status/list/bootstrap), `sg_compute_specs/vault_publish/waker/` (Waker Lambda with FastAPI + LWA), `sgraph_ai_service_playwright__cli/aws/cf/` (CloudFront CRUD), `sgraph_ai_service_playwright__cli/aws/lambda_/` (Lambda deploy + URL CRUD). 5 commits (a5de0b1 P1a → 432ba5d P2d). 149 waker+vault-publish tests + 52 CF/Lambda tests — all passing. |
| 2026-05-16 | v0.2.22: `sg aws billing` CLI sub-package — 6 commands, 4 primitives, 4 enums, 4 schemas, 3 collections, 3 service classes, `Cli__Billing.py`. `Cli__Aws.py` updated to register `billing_app`. 6 commits on `claude/plan-billing-view-u0NFG`. |
| 2026-05-05 | T3.3b: `components/sp-cli/` → `components/sg-compute/` directory rename; 28 api_site/ string refs + 45 sg_compute_specs/*/ui/detail/ absolute imports updated; snapshot test COMPONENT_DIR paths corrected; 32/33 CI green |
| 2026-05-05 | T2.1b: `sg-compute-ami-picker.setSpecId()` wired to `GET /api/amis` via `apiClient`; `_populateAmis()` / `_showLoading()` / `_showError()` / `_hidePlaceholder()` added; 17-assertion snapshot test; T2.1 debrief flipped PARTIAL → COMPLETE; frontend component table added to reality doc |
| 2026-05-05 | T2-FE-patch: `ami_name` threaded to POST body; spec-card body click + keyboard wired; README broken link → placeholder; inline styles → CSS classes; `stability||'unknown'`; 13-assertion snapshot test for spec-detail |
| 2026-05-05 | BV2.12: agent_mitmproxy/ deleted (35 files); tests/unit/agent_mitmproxy/ deleted (12 files); ci__agent_mitmproxy.yml deleted; scripts/provision_ec2.py → sg_compute_specs.mitmproxy; shim task deferred (implementations diverged from sg_compute_specs) |
| 2026-05-05 | BV2.11: Lambda packaging cutover — lambda_entry.py + build_request() → sg_compute_specs.playwright.core; sgraph_ai_service_playwright/ deleted (175 files); pyproject.toml updated; 55 test files bulk-updated; 2151 unit tests pass |
| 2026-05-05 | BV2.10: Fast_API__SP__CLI sub-app mounted at /legacy in Fast_API__Compute (auth preserved); ASGI wrapper injects X-Deprecated: true; run_sp_cli.py → Fast_API__Compute; 356 passing under python3.12 |
| 2026-05-05 | FV2.6 (all 8 specs): ui/{card,detail}/v0/v0.1/v0.1.0/ created in sg_compute_specs for docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox; 48 files moved; api_site/plugins/ deleted; detail imports → absolute /ui/ paths; admin/index.html → /api/specs/<id>/ui/ |
| 2026-05-05 | BV2.19: Spec__UI__Resolver + StaticFiles mount at /api/specs/{spec_id}/ui; ui_root_override for tests; sg_compute_specs/*/ui/**/* in pyproject.toml include; 322 tests passing |
| 2026-05-05 | T2.6b (PARTIAL): Pod__Manager public methods typed (Safe_Str__Node__Id/Safe_Str__Pod__Name); Platform + EC2__Platform public methods typed (Safe_Str__Node__Id/Safe_Str__AWS__Region); routes wrap Safe_Str before calling manager/platform; tests updated; schema fields + spec-side deferred to T2.6c |
| 2026-05-05 | T2.4b: vault_attached=True wired in Fast_API__Compute._mount_control_routes; route test prefix fixed to /api/vault; production PUT path unblocked |
| 2026-05-10 | v0.2.7: Ollama wedge — first spec on `Spec__CLI__Builder`. `Cli__Ollama.py` (≤90 LOC + 3 spec extras: `models/pull/claude`); `Ollama__Service` extends `Spec__Service__Base` with `cli_spec()/pull_model()/claude_session()`; new `Ollama__AMI__Helper` (DLAMI default), `Enum__Ollama__AMI__Base`, `Safe_Str__Ollama__Model` primitive; 4 new user-data sections (`Section__GPU_Verify/Section__Ollama/Section__Claude_Launch/Section__Agent_Tools`); model default `qwen2.5-coder:7b` → `gpt-oss:20b`; instance default `g4dn.xlarge` → `g5.xlarge` (R4); 78 new + 45 existing tests passing |
| 2026-05-10 | v0.2.6: `Spec__CLI__Builder` factory + `Spec__CLI__Resolver` + `Spec__CLI__Errors` + `Spec__CLI__Defaults` + `Schema__Spec__CLI__Spec` + `Spec__Service__Base` + 2 result schemas; `Safe_Int__Exit__Code` primitive; CLI contract doc published; 34 new tests; version bumped to v0.2.6 |
| 2026-05-10 | fix(docker): `--disk-size` wired through `sp docker create` legacy path (`sgraph_ai_service_playwright__cli/docker/`) — was already present on `sg-compute spec docker create` |
| 2026-05-05 | BV2.9: sg_compute/vault/ created (13 files); plugin→spec rename; Routes__Vault__Spec mounted at /api/vault on Fast_API__Compute; 11 legacy shims; 313 tests passing |
| 2026-05-05 | BV2.8: object=None → Optional[T] in 10 non-circular spec service files; 7 circular AWS__Client files kept object=None; Optional import added to 17 files |
| 2026-05-05 | BV2.7: 14 new canonical modules in sg_compute (primitives, enums, event_bus, image); 46 spec files import-rewritten; CI guard added; 584 tests passing |
| 2026-05-05 | FV2.8: dashboard confirmed zero `/containers/*` URL references; CSS comment updated to "Pods tab"; BV2.17 (sidecar alias deletion) now unblocked |
| 2026-05-05 | BV2.5: `EC2__Platform.create_node` + `POST /api/nodes`; `Schema__Node__Create__Request__Base` (spec_id/node_name/region/instance_type/max_hours/caller_ip); docker only — others raise `NotImplementedError` |
| 2026-05-05 | BV2.6: `Spec__CLI__Loader` + `Cli__Docker` pilot; `sg-compute spec docker <verb>` routing; 19 new tests |
| 2026-05-05 | BV2.2: `Section__Sidecar` added to `platforms/ec2/user_data/`; wired into all 10 spec `User_Data__Builder` classes; 17 new tests; 553 passing |
| 2026-05-05 | BV2.3: `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 pod collections, `Routes__Compute__Pods` (6 endpoints); 246 tests passing |
| 2026-05-04 | BV2.4: `Routes__Compute__Nodes` constructor injection; `Schema__Node__List` `total`+`region`; `Exception__AWS__No_Credentials` + 503 handler; BV2.1 orphan delete |
| 2026-05-02 | Phase B3.0: docker spec migrated to `sg_compute_specs/docker/`; 31 new tests; `Spec__Loader` now returns 3 specs |
| 2026-05-02 | Phase B2: foundations — primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver/Registry, Node__Manager, manifest.py for ollama+open_design, helpers moved to platforms/ec2/ |
| 2026-05-02 | Phase B1: `ephemeral_ec2/` renamed to `sg_compute/`; pilot specs moved to `sg_compute_specs/`; domain placeholder created |

---

## See also

- [`primitives.md`](primitives.md) — primitives, enums, core schemas
- [`platform.md`](platform.md) — Platform interface and EC2 platform
- [`specs.md`](specs.md) — spec catalogue, manifests, vault
- [`cli.md`](cli.md) — CLI surface (Spec__CLI__Builder, billing, vault-publish)
- [`pods.md`](pods.md) — pod management + control plane
- [`host-plane.md`](host-plane.md) — pointer to host-control domain
- [`proposed/index.md`](proposed/index.md) — PROPOSED items
- [`../host-control/index.md`](../host-control/index.md) — sibling domain documenting the host-control HTTP surface
