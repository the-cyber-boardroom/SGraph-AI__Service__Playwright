# Reality — SG/Compute Domain

**Status:** ACTIVE — seeded in phase-1 (B1), foundations added in phase-2 (B2), pod management in BV2.3, CLI builder in v0.2.6, billing CLI in v0.2.22, vault-publish spec in v0.2.23, vault-app fargate in v0.2.33, admin Lambda split in v0.1.16.
**Last updated:** 2026-05-19 | **Phase:** v0.2.33 (vault-app fargate — Fargate-based vault container lifecycle) + v0.1.16 (vault-publish admin Lambda split — `lambdas/{waker,admin}/` + dedicated `vp-admin.aws.sg-labs.app` distribution)

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

### sg_compute/cli/ — EXISTS (v0.2.25)

| Class / File | Path | Description |
|--------------|------|-------------|
| `Cli__SG` | `cli/Cli__SG.py` | Top-level `sg` Typer app; mounts `credentials` + `osx` subapps |
| `Cli__SG__Repl` | `cli/Cli__SG__Repl.py` | Interactive REPL; `as <role>` pseudo-command; `Ctrl-C` clears role |

### sgraph_ai_service_playwright__cli/credentials/ — EXISTS (v0.2.25)

| Class | Path | Description |
|-------|------|-------------|
| `Enum__Credential__Kind` | `credentials/enums/Enum__Credential__Kind.py` | ROLE/AWS/VAULT/SECRET/ROUTES |
| `Enum__Audit__Action` | `credentials/enums/Enum__Audit__Action.py` | ADD/REMOVE/SWITCH/EDIT/EXPORT/ASSUME/LIST/SHOW/STATUS |
| `Safe_Str__Role__Name` | `credentials/primitives/` | lowercase alphanum + hyphens, max 64 |
| `Safe_Str__AWS__Region` | `credentials/primitives/` | e.g. `us-east-1` |
| `Safe_Str__AWS__Access__Key` | `credentials/primitives/` | repr=`****` |
| `Safe_Str__AWS__Secret__Key` | `credentials/primitives/` | repr=`****` |
| `Safe_Str__AWS__Role__ARN` | `credentials/primitives/` | ARN format, mixed case |
| `Safe_Str__Audit__Detail` | `credentials/primitives/` | printable ASCII, max 512 |
| `Schema__AWS__Role__Config` | `credentials/schemas/` | name + region + assume_role_arn + session_name |
| `Schema__AWS__Credentials` | `credentials/schemas/` | role_name + access_key + secret_key |
| `Schema__Audit__Event` | `credentials/schemas/` | timestamp + action + role + detail |
| `Credentials__Store` | `credentials/service/` | high-level keyring ops; maps roles↔keyring service names |
| `Audit__Log` | `credentials/service/` | append-only JSONL at `~/.sg/audit.jsonl` |
| `Sg__Aws__Context` | `credentials/service/` | session-level active role; `set_role()` / `clear_role()` |
| `Sg__Aws__Session` | `credentials/service/` | vends `boto3.Session` for a role; STS AssumeRole if ARN set |
| `Cli__Credentials` | `credentials/cli/` | `sg credentials.*` Typer subapp (list/add/remove/switch/show/status/log/trace/export) |

### sgraph_ai_service_playwright__cli/osx/ — EXISTS (v0.2.25)

| Class | Path | Description |
|-------|------|-------------|
| `Enum__Keyring__Service` | `osx/keyring/enums/` | sg.config.role / sg.config.routes / sg.aws / sg.vault / sg.secret |
| `Safe_Str__Keyring__Account` | `osx/keyring/primitives/` | lowercase alphanum + hyphens/dots/underscores |
| `Safe_Str__Keyring__Service_Name` | `osx/keyring/primitives/` | same character set |
| `Safe_Str__Secret__Value` | `osx/keyring/primitives/` | repr=`****` |
| `Schema__Keyring__Entry` | `osx/keyring/schemas/` | service_name + account |
| `Keyring__Mac__OS` | `osx/keyring/service/` | `/usr/bin/security` wrapper; override `_run_security()` in tests |
| `Cli__OSX__Keyring` | `osx/keyring/cli/` | `sg osx keyring.*` (get/set/delete/list/search) |
| `Cli__OSX` | `osx/cli/` | `sg osx` root app |

### Keyring service namespacing — EXISTS (v0.2.25)

| Namespace | Format | Stores |
|-----------|--------|--------|
| `sg.config.role.<name>` | account=`config` | JSON role config blob |
| `sg.config.routes` | account=`routes` | JSON route list |
| `sg.aws.<role>` | account=`access_key` / `secret_key` | AWS credentials pair |
| `sg.vault.<name>` | account=`<name>` | vault key |
| `sg.secret.<ns>.<name>` | account=`<name>` | arbitrary secret |

### Audit log — EXISTS (v0.2.25)

JSONL file at `~/.sg/audit.jsonl`. One event per line: `{timestamp, action, role, detail}`. Secrets never written. Read via `Audit__Log.read_all()` / `.tail(n)`.

### Entry points (v0.2.25)

| Script | Module | Description |
|--------|--------|-------------|
| `sg` | `sg_compute.cli.Cli__SG:app` | top-level sg CLI |
| `sg-repl` | `sg_compute.cli.Cli__SG__Repl:run_repl` | interactive REPL |

---

## vault-app fargate (v0.2.33)

`sg vault-app fargate` — Fargate-based vault container lifecycle.

Setup commands (cluster-level, one-time):

```
setup check / status / create / update / delete / plan / show
```

Task-level commands (per vault session):

```
start / stop / restart / health / url / open / logs / list / info / timings
```

File layout: `sg_compute_specs/vault_app/fargate/`

```
cli/      — Cli__Vault_App__Fargate.py, __Setup.py, __Start.py
service/  — Vault_App__Fargate__Setup, Vault_App__Fargate__Starter,
             Vault_App__Fargate__Spec, Vault_App__Fargate__Tags__Reader/Writer,
             Vault_App__Fargate__Cluster__Resolver, Vault_App__Fargate__Slug__Resolver,
             Vault_App__Fargate__Health, Vault_App__Fargate__Image__Mirror,
             Vault_App__Fargate__Timings__Store, Phase__Timer,
             Phase__Progress__Renderer, Mutation__Gate__Scope
schemas/  — Schema__VAF__Cluster__Config, Schema__VAF__Start__Request/Report,
             Schema__VAF__Setup__Request/Report, Schema__Phase__Result,
             Schema__VAF__Timings__Record, Schema__VAF__Health__Result
enums/    — Enum__VAF__Phase__Status, Enum__VAF__Setup__Phase, Enum__VAF__Start__Phase
primitives/ — Safe_Str__VAF__Slug, Safe_Str__VAF__Cluster
```

Mutation gate: `SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1`

AWS resources managed: ECS cluster, task definition, ECR repo, IAM execution role,
CloudWatch log group.

Tests: `tests/unit/sg_compute_specs/vault_app/fargate/` — 410 tests.

Spec doc: [`library/docs/specs/v0.2.33__vault-app-fargate.md`](../../../../../library/docs/specs/v0.2.33__vault-app-fargate.md)

Onboarding guide: [`library/onboarding/v0.2.33__vault-app-fargate.md`](../../../../../library/onboarding/v0.2.33__vault-app-fargate.md)

---

## sg_edge — Phase 1 foundation (v0.2.37)

`sg_compute_specs/sg_edge/` — typed foundation for the SG/Edge central edge tier (Slice 1 of the Phase 1 plan). AWS-call-free; pure Type_Safe data + the two shared DNS-TXT composer/parsers. The wider SG/Edge build (Edge Waker FastAPI Lambda, proxy fleet, CloudFront wiring) is PROPOSED — see [`proposed/index.md`](proposed/index.md) P-7 and the plan at `team/comms/plans/v0.2.37__sg-edge/`.

**Aligned to the 2026-05-20 brief rewrite (`647de5a`):** module is `sg_edge` (not `edge`); there is **no S3 lock** — the Edge Waker is convergent and all its state lives in DNS (`proxies.<parent>` A records + a `_state.<parent>` TXT counter). The earlier S3-lock fleet-state schema and IP-list collection were dropped.

| Class / File | Path | Description |
|--------------|------|-------------|
| `Safe_Str__SG_Edge__Parent_Domain` | `sg_edge/primitives/` | Parent domain that defines one edge (e.g. `cv.sgraph.ai`) |
| `Safe_Int__SG_Edge__Unix_Ts` | `sg_edge/primitives/` | Unix timestamp (TXT `launched`, `_state` `updated`); 0 = unset |
| `Safe_Int__SG_Edge__TXT_Version` | `sg_edge/primitives/` | TXT schema `v=` field; defaults to 1, only v=1 valid today |
| `Safe_Int__SG_Edge__Cycle_Count` | `sg_edge/primitives/` | Non-negative scheduled-check counter (`_state` `zero_streak`) |
| `Enum__SG_Edge__Backend__Type` | `sg_edge/enums/` | `ec2` / `fargate` — the routing-TXT `type=` token |
| `Enum__SG_Edge__Fleet__State` | `sg_edge/enums/` | Fleet status labels: `zero`/`booting`/`active`/`scaling`/`draining` (descriptive; reconciliation, not a coordinator) |
| `Schema__SG_Edge__TXT__Record` | `sg_edge/schemas/` | Typed form of the `_sg.<slug>` routing TXT record |
| `Schema__SG_Edge__State__Record` | `sg_edge/schemas/` | Typed form of the `_state.<parent>` TXT (zero_streak + updated) |
| `SG_Edge__TXT__Builder` | `sg_edge/service/` | Composes/parses the v=1 routing TXT; shared by Vault Waker + Reaper |
| `SG_Edge__State__Builder` | `sg_edge/service/` | Composes/parses the `_state.<parent>` TXT counter |
| `SG_Edge__DNS__Helper` | `sg_edge/service/` | Edge control-plane DNS surface over `sg aws dns`: `proxies.<parent>` A membership (list/add/remove/count), `_state.<parent>` TXT read/write, `_sg.*` active-slug count + routing read (Slice 2) |
| `Schema__SG_Edge__Proxy` | `sg_edge/schemas/` | A launched, health-green proxy (instance_id + ip) returned by the launcher seam (Slice 3) |
| `SG_Edge__Fleet__Reconciler` | `sg_edge/service/` | Convergent control loop — `ensure_booting` (cold-cold), `reconcile` (scale check), `idle_check` (zero_streak teardown); AWS work behind launcher/terminator/clock seams (Slice 3) |
| `Fast_API__Edge_Waker` + `Routes__Edge_Waker` + `Loading__Page` + `lambda_entry` + `edge_waker__config` | `sg_edge/lambdas/edge_waker/` | The Edge Waker as a `Serverless__Fast_API` Lambda (same pattern as `vault_publish/lambdas/waker/` + combined-deps loader). Routes: `/__edge__/health|status|reconcile|idle-check` + cold-cold loading-page catch-all (Slice 3) |
| `proxy/nginx.conf` + `SG_Edge__Proxy__User_Data` | `sg_edge/proxy/`, `sg_edge/service/` | Phase 1 OpenResty static-diagnostic rig (`:80`, `/_edge/health|stats|version|slug_seen`, IP-redacted access log) + the EC2 cloud-init user-data builder that runs it (Slice 4) |
| `cloudfront_function/viewer_request.js` + `SG_Edge__CloudFront__Function` | `sg_edge/cloudfront_function/`, `sg_edge/service/` | CloudFront viewer-request function (Host preserve + slug → `X-SG-Slug`/`X-SG-Host`) + its loader (Slice 4) |
| `Edge_Bench__Runner` + `Edge_Bench__Stats` + `Schema__Edge_Bench__Metric` + `Enum__Edge_Bench__Verdict` | `sg_edge/bench/` | The doc-05 measurement core: percentiles (nearest-rank) + acceptance-threshold verdicts (PASS/WARN/FAIL on target vs hard_fail) over repeated scenario runs (Slice 6 core) |

Tests: `sg_compute_specs/sg_edge/tests/` — 72 unit tests + 6 FastAPI route tests (skipped off Python 3.12). Logic (builders, DNS helper, reconciler, proxy user-data, bench runner) is fully covered against the real in-memory fakes; the FastAPI surface is TestClient-tested in CI. No mocks. Purely additive — nothing outside `sg_edge/` imports it; the `sg` CLI surface is unchanged.

**Phase 1 status:** Slices 1–4 (typed foundation, DNS helper, Edge Waker FastAPI Lambda + reconciler, proxy rig + CF function) and the Slice 6 bench measurement core are landed and tested. Remaining Phase 1 work is **live-environment-bound** (not buildable/verifiable in the CI container): the EC2-backed proxy launcher/terminator wiring + the CF/ACM/IAM/Lambda Setup orchestration (deploy-via-pytest against real AWS), and the `sg edge_bench` docker-compose local stack + live scenario bodies (P-*/F-*/X-*).

---

## vscode — VS Code on EC2 (v0.2.41, in progress)

`sg_compute_specs/vscode/` — new top-level compute spec: an ephemeral EC2 node running web/browser VS Code (code-server, with `code serve-web` behind a distribution enum), reachable via SSM port-forward (default, no inbound ports) or public HTTPS (Caddy + auth). Spec: [`library/docs/specs/v0.2.41__spec__vscode-on-ec2.md`](../../../../library/docs/specs/v0.2.41__spec__vscode-on-ec2.md); proposed entry P-8.

**Slice status:**

| Slice | What | Status |
|-------|------|--------|
| 1 | Package skeleton + `manifest.py` + `version` + contract test + `pyproject` entry point | ✅ EXISTS — `Spec__Loader` discovers `vscode` (16 specs); `tests/test_manifest.py` (6 tests) |
| 2 | SSM_FORWARD mode end-to-end (schemas, `Vscode__Service`, `Vscode__User_Data__Builder`, `Vscode__Compose__Template`, `Vscode__Stack__Mapper`, CLI + top-level mount) | ✅ EXISTS — `sg vscode` (alias `vsc`) mounted; `create/list/info/wait/health/connect/exec/delete/ami/cert` from the builder + `forward`/`url`; 17 unit tests pass |
| 3 | PUBLIC_HTTPS mode (`Vscode__Caddy__Template` + `--ingress public-https` + `--public`) | ✅ EXISTS — Caddy `tls internal` :443 → code-server (code-server's own password auth; shared `EC2__SG__Helper` opens :443/:80, caller /32 or 0.0.0.0/0). code-server stays loopback-published so forward/health are mode-independent |
| 4 | Auto-DNS + real cert (reuse `Vault_App__Auto_DNS`) | ❌ not yet |
| 5 | `serve-web` distribution branch | ❌ not yet |
| 6 | TUI (`sg vscode tui`) — GUI over the CLI | ❌ not yet |

Net-new, additive — nothing outside `sg_compute_specs/vscode/` imports it until the top-level mount (Slice 2). EC2/AWS-bound behaviour is verified via deploy-via-pytest (skips without creds); unit tests cover schemas, user-data content, stack-mapper, and SG naming.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## History

| Date | Change |
|------|--------|
| 2026-05-20 | v0.2.37 SG/Edge Slice 1 (typed foundation): new `sg_compute_specs/sg_edge/` spec — 4 primitives, 2 enums, 2 schemas (`Schema__SG_Edge__TXT__Record` routing + `Schema__SG_Edge__State__Record` `_state` counter), 2 builders (`SG_Edge__TXT__Builder`, `SG_Edge__State__Builder`). 32 unit tests, no AWS calls, purely additive. Plan: `team/comms/plans/v0.2.37__sg-edge/`. Re-grounds the 05/20 briefs onto existing `sg aws *` modules + the `Serverless__Fast_API` Lambda pattern. Realigned to the 2026-05-20 brief rewrite (`647de5a`): module `sg_edge` not `edge`; S3 lock removed (convergent reconciliation; state in DNS). Branch: `claude/implement-sg-edge-agent-c2jEp`. |
| 2026-05-19 | v0.1.16 vault-publish admin Lambda split: `sg_compute_specs/vault_publish/waker/` and `sg_compute_specs/vault_publish/admin/` moved under `sg_compute_specs/vault_publish/lambdas/{waker,admin}/` (deployment-unit grouping). New admin Lambda `sg-compute-vault-publish-admin` with own IAM role + CloudFront distribution + single-host ACM cert at `vp-admin.aws.sg-labs.app` — defeats H2 connection coalescing for the warming-page status probe. Setup pieces: `Setup__Admin__IAM`, `Setup__Admin__Lambda`, `Setup__Admin__CF` (includes cert provisioning + wildcard-cert guard), `Setup__Admin__DNS`. New CLI sub-apps `sg vp setup admin-iam/lambda/cf/dns *`. `setup create / update` reorder admin BEFORE waker so the warming page's probe target is always live. `Fast_API__Waker.py` deleted (dead code post-split). Warming page polls `https://vp-admin.aws.sg-labs.app/api/v1/status` by default. 16 warming-page tests passing. Branch: `claude/waker-debug-clean-bRIbm`. |
| 2026-05-19 | v0.2.33: vault-app fargate — `sg vault-app fargate` sub-app (setup/start), `Phase__Timer`, `Phase__Progress__Renderer`, `Mutation__Gate__Scope`, 12 service classes, 7 schemas, 3 enums, 2 primitives under `sg_compute_specs/vault_app/fargate/`. Pre-work: `sg aws fargate` Slice 0a (task-def/task-run essential flags), `sg aws ec2 eni` Slice 0b, `sg aws logs` Slice 0c. 410 fargate unit tests. Branch: `claude/review-vault-publish-spec-FT9hq`. |
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
