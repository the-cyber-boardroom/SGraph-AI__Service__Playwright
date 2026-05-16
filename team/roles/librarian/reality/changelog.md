# Reality — Changelog

**Format:** `Date | Domain file(s) updated | One-line description`

This is a pointer log, not a content log. For full delta detail, see the master index for that date in `team/roles/librarian/reviews/MM/DD/` (folder created on first review) or the linked domain `index.md`.

---

## 2026-05-15 (sg aws dns + acm — P0 + P1 + P1.5 + ergonomics shipped)

- `v0.1.31/16__sg-aws-dns-and-acm.md` — NEW: full per-zone DNS management surface (`sg aws dns zones list`, `dns zone show/list/check/purge`, `dns records add/update/delete/check/get/list`, `dns instance create-record`) + ACM inventory (`sg aws acm list/show`). 136 unit tests, no mocks. `Route53__AWS__Client` + `ACM__AWS__Client` are the boto3 boundaries. Default mode is zero-cache-pollution (authoritative-NS direct via `dig @ns +norecurse`); cache-polluting modes opt-in behind verbatim WARNING banners. `zone check` cross-references ACM cert validation CNAMEs to identify orphaned records; `zone purge` batch-deletes ORPHANED + STALE A records in a single Route 53 ChangeBatch. Wired into `sg_compute/cli/Cli__SG.py`. Brief: `team/humans/dinis_cruz/claude-code-web/05/15/08/architect__sg-aws-dns__plan.md`. Debriefs under `team/claude/debriefs/2026-05-15__sg-aws-dns-*`.
- `v0.1.31/README.md` — Index updated with row 16.

---

## 2026-05-05 (T2.2b — Firefox credentials + mitm-script routes)

- `sg-compute/index.md` — UPDATED: `Schema__Firefox__Credentials__Response`, `Schema__Firefox__Mitm__Script__Response`, `Firefox__SSM__Helper` added to firefox spec. `Firefox__Service` gains `set_credentials` + `upload_mitm_script`. `Routes__Firefox__Stack` gains `PUT /{node_id}/credentials` + `PUT /{node_id}/mitm-script`. `Cli__Firefox` `NotImplementedError` removed; both CLI commands fully wired.

---

## 2026-05-05 (BV__caller-ip-endpoint)

- `sg-compute/index.md` — UPDATED: `Schema__Caller__IP` added to `sg_compute/catalog/schemas/`; `Routes__Compute__Catalog` added to control plane routes (`GET /catalog/caller-ip`); `/catalog/caller-ip` added to `_AUTH_FREE_PATHS`. Frontend: `sg-compute-launch-form._seedCallerIp()` calls backend on remote hosts; "Find my public IP" link removed.

---

## 2026-05-05 (BV__spec-readme-endpoint)

- `sg-compute/index.md` — UPDATED: `Spec__Readme__Resolver` added to `core/spec/` table; `Routes__Compute__Specs` description updated with `GET /api/specs/{spec_id}/readme`; `Fast_API__Compute` `readme_root_override` field added. `sg_compute_specs/firefox/README.md` created. `sg_compute_specs/pyproject.toml` includes `*/README.md` in package-data.

---

## 2026-05-05 (T2.7b — docstring sweep complete)

- `sg-compute/index.md` — NO CHANGE (no new code, only style/format cleanup): all `"""..."""` template string constants converted to `'''...'''` across `sg_compute/platforms/ec2/user_data/` (Section__*) and `sg_compute_specs/*/service/` builders and templates (28 files). Method docstrings deleted from `Cli__Firefox`, `Browser__Launcher`, `Playwright__Service`. `grep -rln '^\s*"""' sg_compute/ sg_compute_specs/` → zero hits.

---

## 2026-05-05 (T2.6c — pod schema primitives + spec-side service sweep)

- `sg-compute/index.md` — UPDATED: 5 new primitives (`Safe_Str__Docker__Image`, `Safe_Str__Log__Content`, `Safe_Int__Log__Lines`, `Safe_Int__Pids`, `Safe_Int__Max__Hours`); all 5 pod schemas fully typed; `Pod__Manager` schema construction sites wrap sidecar values; `Docker__Service`, `Podman__Service`, `Vnc__Service` public methods typed; 3 `*__User_Data__Builder.render()` typed; `EC2__Platform.create_node` wraps SSM path.

---

## 2026-05-05 (T2.6b PARTIAL — Safe_Str public method signatures)

- `sg-compute/index.md` — UPDATED: `Pod__Manager` public methods typed with `Safe_Str__Node__Id`/`Safe_Str__Pod__Name`; `Platform` + `EC2__Platform` public methods typed; routes wrap Safe_Str before calling manager/platform. Schema fields + spec-side deferred to T2.6c.

---

## 2026-05-05 (T2.4b — vault production wiring fixed)

- `sg-compute/index.md` — UPDATED: `Vault__Spec__Writer` description updated; `vault_attached=True` now wired in `Fast_API__Compute._mount_control_routes`; route test prefix fixed to `/api/vault`; "persistence stubbed" removed from description.

---

## 2026-05-05 (FV2.6 — all 8 specs complete)

- `sg-compute/index.md` — UPDATED: 48 files moved to `sg_compute_specs/{spec}/ui/{card,detail}/v0/v0.1/v0.1.0/` for docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox; `api_site/plugins/` deleted; all per-spec detail dirs in `api_site/components/sp-cli/` deleted; all detail JS imports → absolute `/ui/` paths; `admin/index.html` all spec script tags → `/api/specs/<id>/ui/...`.

---

## 2026-05-05 (BV2.7)

- `sg-compute/index.md` — UPDATED: 14 new canonical modules (primitives, enums, event_bus, image); 46 spec files import-rewritten from `__cli.*` to `sg_compute.*`; CI guard added; 584 tests passing.

---

## 2026-05-05 (BV2.6)

- `sg-compute/index.md` — UPDATED: `Spec__CLI__Loader` + `Cli__Docker` pilot; `sg-compute spec docker <verb>` dispatcher; 19 new tests.

---

## 2026-05-05 (BV2.5)

- `sg_compute/control_plane/routes/Routes__Compute__Nodes.py` — UPDATED: added `POST /api/nodes` (`create_node`)
- `sg_compute/platforms/ec2/EC2__Platform.py` — UPDATED: `create_node` dispatches on `spec_id`; `_create_docker_node` live
- `sg_compute/control_plane/lambda_handler.py` — NEW: Mangum wrapper for Lambda deployment
- `sg_compute__tests/control_plane/test_lambda_handler.py` — NEW: 3 smoke tests. 235 passing.

---

## 2026-05-05 (BV2.2)

- `sg-compute/index.md` — UPDATED: `Section__Sidecar` added to platforms/ec2/user_data/; wired into all 10 spec User_Data__Builder classes (8 template-based, 2 parts-based); PLACEHOLDERS tuples updated; 17 new sidecar tests; 553 passing.

---

## 2026-05-05 (BV2.3)

- `sg-compute/index.md` — UPDATED: BV2.3 pod management added; `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 collections, `Routes__Compute__Pods` (6 endpoints), `Routes__Compute__Nodes` constructor injection. 246 tests passing.

---

## 2026-05-04 (BV2.4)

- `sg_compute/control_plane/routes/Routes__Compute__Nodes.py` — REFACTORED: constructor injection, typed schema returns, no business logic
- `sg_compute/control_plane/Fast_API__Compute.py` — UPDATED: platform field, `Exception__AWS__No_Credentials` handler registered
- `sg_compute/platforms/exceptions/` — NEW: `Exception__AWS__No_Credentials`
- `sg_compute/core/node/schemas/Schema__Node__List.py` — UPDATED: `total` and `region` fields added
- `sg_compute__tests/control_plane/test_Routes__Compute__Nodes.py` — REWRITTEN: zero mocks. Commit: 7ca8b96.

---

## 2026-05-04 (BV2.1)

- `host-control/index.md` — UPDATED: `sgraph_ai_service_playwright__host/` deleted (orphaned copy confirmed by legacy review); authoritative package is `sg_compute/host_plane/`; port corrected `:9000` → `:19009`; tests and pyproject.toml reference removed. Commit: `0517528`.

---

## 2026-05-02 (B3.0)

- `sg-compute/index.md` — UPDATED: B3.0 docker spec added; `sg_compute_specs/docker/` fully documented; Spec__Loader now returns 3 specs; 183 tests passing.

---

## 2026-05-02

- `sg-compute/index.md` — UPDATED: phase-2 (B2) foundations; primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver, Node__Manager, manifest.py for pilot specs; helpers moved to platforms/ec2/. 152 tests passing.
- `sg-compute/index.md` — NEW: SG/Compute domain placeholder; seeded by phase-1 (B1) rename commit. `ephemeral_ec2/` → `sg_compute/`; `sg_compute_specs/` introduced with pilot specs (ollama, open_design). Full domain content lands in phase-2 (B2).
- `index.md` — UPDATED: added `sg-compute/` domain row; domain count 10 → 11.
- `index.md` — NEW: master domain index created (reality document refactor begins; 10-domain tree introduced).
- `README.md` — UPDATED: explains the new fractal model and the migration shim.
- `host-control/index.md` — NEW: pilot domain migration; `sgraph_ai_service_playwright__host` package (container runtime abstraction, shell executor, three Routes__Host__* classes, EC2 boot wiring). Sourced from commit `11c2a08`.
- `host-control/proposed/index.md` — NEW: WebSocket shell streaming hardening, RBAC for host endpoints, runtime auto-detection feedback in UI.
- `../DAILY_RUN.md` — NEW: daily routine + backlog (B-001 … B-010 = per-domain migration queue + housekeeping).
- `../activity-log.md` — NEW: session-continuity stub with first entry.

---

## Entries before 2026-05-02

Reality was tracked as version-stamped monoliths under this folder. The most recent split was `v0.1.31/01..15__*.md` (2026-04-20 → 2026-04-29). Earlier monoliths: `v0.1.13`, `v0.1.24`, `v0.1.29` `__what-exists-today.md`. None of those had a per-update changelog entry; this changelog starts from the domain-tree introduction.

For history pre-2026-05-02, read the relevant `v0.1.31/NN__*.md` slice or the archived monolith.
