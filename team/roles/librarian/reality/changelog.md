# Reality — Changelog

**Format:** `Date | Domain file(s) updated | One-line description`

This is a pointer log, not a content log. For full delta detail, see the master index for that date in `team/roles/librarian/reviews/MM/DD/` (folder created on first review) or the linked domain `index.md`.

---

## 2026-05-23 (SG/Sentinel — operator TUIs + traffic generator / httpget echo server)

2026-05-23 | sentinel | Added `sg sentinel tui rules|logs|blocks|status` (Textual,
  MVP-backed; pure renders + thin screens + --json/no-TTY) and `sg sentinel traffic`
  (use-case corpus replayed in-process through L1+L2 or over HTTP) + `sg sentinel echo
  serve` (dependency-free httpget echo origin; same Echo__Payload on local/docker/Lambda/
  EC2) for rule testing + impact measurement. Added Safe_Str__Sentinel__Version. Branch only.

- `sentinel/index.md` — updated EXISTS: TUIs (`tui/`) + traffic generator/echo (`traffic/`).

## 2026-05-23 (SG/Sentinel MVP — Phases 0–5, branch `claude/gracious-galileo-fNYWn`)

2026-05-23 | sentinel (NEW), cli, security | SG/Sentinel edge-guard MVP: new
  `sg sentinel` peer surface (logging + obvious-bad blocking), L1 CF Function
  decides+signals → L2 Lambda@Edge acts+writes, three targets (local-direct /
  local-docker / live AWS) over one `Schema__Sentinel__Signal` spine. Shared
  `aws/_shared/auth` gained `Schema__AWS__Role__Profile.trust_services` (Lambda@Edge
  exec-role trust — approved option a); `aws/cf|lambda_|s3` gained L@E association,
  numbered-version publish, and bucket delete/empty (EXCEPTION-headed). Not yet on `dev`.

- `sentinel/index.md` — NEW domain: CLI surface, signal spine, L1 engine + 6 rules,
  L2 actor + sinks, the three targets, role profiles, parity matrix, known gaps.
- `sentinel/proposed/index.md` — NEW: the deferred v0.27.58 vision (incl. the TUI).

## 2026-05-21 (v0.2.40 — shared AWS auth layer + sg el lets cf iam)

2026-05-21 | cli, lets | v0.2.40 shared AWS auth layer (`aws/_shared/auth/`):
  credential chokepoint convergence (CloudFront/Logs/Firehose + LETS S3 boundaries),
  `NoCredentialsError` guard/menu, role-profile registry, role provisioner,
  transparent assume of `sg-lets-cf`, and the `sg el lets cf iam` sub-app.

- `cli/aws-auth.md` — NEW: the full engine — chokepoint (`Aws__Session__Factory`), guard (`AWS__Auth__Classifier`/`AWS__Auth__Guard`), registry (`AWS__Role__Profiles` + profile/statement schemas), provisioner (`AWS__Role__Provisioner` + `Schema__AWS__Role__Plan`), transparent assume (`AWS__Auth__Context`/`AWS__Auth__Resolver`), `IAM__AWS__Client.create_role_with_trust`/`update_assume_role_policy_raw`, `Sg__Aws__Session.assume_arn`/`account_id_via_sts`. Wiring matrix + caveats (live IAM/STS unverified).
- `lets/index.md` — UPDATED: `sp el lets cf iam show|plan|create|update|test|delete` added to the CLI surface; v0.2.40 auth-guard + transparent-assume subsection.
- `cli/index.md` — UPDATED: rows for `aws-auth.md` and `sg el lets cf iam`.

---

## 2026-05-19 (v0.2.33 — vault-app fargate: sg vault-app fargate sub-app)

2026-05-19 | sg-compute, cli | v0.2.33 vault-app fargate: `sg vault-app fargate` sub-app
  (setup/start), `Phase__Timer`, `sg aws fargate` essential flags (Slice 0a),
  `sg aws ec2 eni` (Slice 0b), `sg aws logs` (Slice 0c); 410 fargate tests.

- `sg-compute/index.md` — UPDATED: `vault-app fargate` section added. File layout, service classes, schemas, enums, primitives, mutation gate, test count, spec + onboarding doc links.
- `cli/aws-fargate.md` — UPDATED: v0.2.33 Slice 0a additions — `task-def register` gains `--port-mapping`, `--execution-role-arn`, `--task-role-arn`, `--log-group`; `task run` gains `--launch-type`, `--tag`, `--env`; `cluster create` gains `--tag`; `Schema__ECS__Port_Mapping` added; `Schema__ECS__Task` and `Schema__ECS__Task__Definition` extended.
- `cli/aws-ec2.md` — UPDATED: v0.2.33 Slice 0b additions — `sg aws ec2 eni list/show`, `Schema__EC2__ENI`, `Safe_Str__EC2__ENI_Id`, `Cli__EC2__Eni.py`.
- `cli/aws-logs.md` — NEW: `sg aws logs` — CloudWatch log group management + tailing (Slice 0c). 5 commands, 2 primitives, 5 schemas, 3 service classes. Mutation gate `SG_AWS__LOGS__ALLOW_MUTATIONS`.
- `cli/index.md` — UPDATED: rows for `aws-logs.md`, `sg aws ec2 eni`, `sg vault-app fargate`.
- `library/docs/specs/v0.2.33__vault-app-fargate.md` — NEW: contract spec (two-mode shape, command tree, tag schema, setup/start phases, JSON envelope, mutation gate, v1 exclusions).
- `library/onboarding/v0.2.33__vault-app-fargate.md` — NEW: "3 commands to run a vault on Fargate" quick-start guide.
- `library/catalogue/README.md` — UPDATED: version bumped to v0.2.33; v0.2.33 notable additions table.

---

## 2026-05-17 PM-late (Librarian finalisation — M-013 / M-014 / M-015 / M-016)

- `.claude/CLAUDE.md` — FIX (M-013): line 96 endpoint count reconciled. Was "25 endpoints — 3 health + 5 session + 16 browser (Layer 0) + 1 sequence (Layer 3)" (stale; Routes__Session removed in v0.1.24). Now: "16 direct endpoints (3 health + 6 browser + 2 screenshot + 1 sequence + 1 metrics + 1 index + 2 auth set-cookie) + admin surface (~4 from Agentic_FastAPI parent)".
- `reality/playwright-service/index.md` — REWRITE (M-014): VERIFY markers closed. All `sgraph_ai_service_playwright/` paths (deleted in BV2.11) updated to `sg_compute_specs/playwright/core/`. Endpoint count corrected: **16 direct + 8 admin**. Service-class count corrected from "9-10" to **11** (added Sequence__Dispatcher, Request__Watchdog, JS__Expression__Allowlist, Credentials__Loader, Capability__Detector). Image moved from Lambda/ECR to Docker Hub (`diniscruz/sg-playwright`). (208 lines, under 300-line cap.)
- `reality/agent-mitmproxy/index.md` — REWRITE (M-014): VERIFY markers closed. Package path `agent_mitmproxy/` → `sg_compute_specs/mitmproxy/` (BV2.12). Route count corrected: 6 → **7** (added `Routes__Web` wildcard + `Prometheus_Metrics` first-class). Critical correction: `Routes__Web` accepts ALL HTTP methods (PUT/DELETE/PATCH), not GET-only as v0.1.33 reality doc claimed → INC-007 minted.
- `reality/ui/index.md` — RESTRUCTURE (M-014): VERIFY markers closed. `api_site/components/sp-cli/` → `sgraph_ai_service_playwright__api_site/components/sg-compute/` (T3.3b). Plugin directories `api_site/plugins/` deleted; per-plugin UI moved to `sg_compute_specs/{spec}/ui/{card,detail}/v0/v0.1/v0.1.0/` (FV2.6). 8 specs with UI today (docker, podman, elastic, vnc, prometheus, opensearch, neko, firefox). Layout key bumped `sp-cli:admin:root-layout:v1` → `v3` (2-column shape, was 3-column).
- `reality/qa/index.md` + `reality/infra/index.md` — UPDATES (M-014): agent_mitmproxy unit tests (was 34+1 in `tests/unit/agent_mitmproxy/`) rebuilt under `sg_compute_specs/mitmproxy/tests/` (12 files, 39 functions). `test_provision_mitmproxy_ec2.py` is now a single `@pytest.mark.skip` placeholder → INC-006 minted. `ci__agent_mitmproxy.yml` workflow deleted (BV2.12); mitmproxy now exercised by `ci-pipeline.yml run-unit-tests`. CI restructured: no more `deploy-code`/`provision-lambdas`/`build-and-push-image (single)`; current jobs are `run-unit-tests`, `check-aws-credentials`, `detect-changes`, `increment-tag`, `build-playwright-image` (per-arch matrix → Docker Hub), `build-and-push-host-image`. `scripts/provision_ec2.py` and repo-root `docker-compose.yml` confirmed deleted (per-launch compose via `Playwright__Compose__Template`).
- `library/catalogue/findings.md` — REFRESH (M-016): `.md` 724→825 (+101), `.py` 2169→2701 (+532), oversized `.md` 97→108, domains migrated 7→11 ✅, broken links 19→0 ✅. `provision_ec2.py` struck from INC-003 (file removed). 4 new INCs registered (004, 005, 006, 007); 2 new M-IDs minted (M-018 plugin sub-folder verification, M-019 SIDECAR_ATTACH UI affordance gap).
- `library/catalogue/_snapshots/v0.2.28/` — NEW (M-016): point-in-time freeze of all 8 catalogue shards against commit `759dfaa`. README pins context.
- `reality/` (multiple fixes) — M-015: 5 depth-miscalculated relative paths fixed (`vault/proposed/`, `cli/proposed/`, `host-control/`, `cli/aws-creds.md`, `cli/aws-ec2.md`, archive `06__sp-cli-duality-refactor.md`). 12 forward refs to `infra/`/`lets/`/`qa/`/`security/` auto-resolved when M-003 landed those domains. Final broken-link count: **0**.

---

## 2026-05-17 (v0.2.30 Open-2 — typed primitives hygiene pass — 91 raw-str fields replaced)

91 raw `str` fields across 6 AWS service schemas replaced with `Safe_Str__*` typed primitives. Three JSON-blob escape hatches in `Schema__EC2__Instance__Detail` replaced with typed collections. Debrief: `team/claude/debriefs/2026-05-17__v0.2.30-open-2-typed-primitives.md`. Key commits: `785a71a`, `1070da0`, `03fc2f9`, `17b9bf9`.

- `cli/aws-ec2.md` — UPDATED: 20 new EC2 primitives + `Safe_Int__EC2__GiB`; new schemas `Schema__EC2__Security_Group__Ref`, `Schema__EC2__Block_Device__Mapping`; new collections `Dict__EC2__Tag`, `List__Schema__EC2__Security_Group__Ref`, `List__Schema__EC2__Block_Device__Mapping`; escape-hatch section added.
- `cli/aws-fargate.md` — UPDATED: 9 new ECS primitives (`Cluster_Arn`, `Status`, `Task__Family`, `Task__Def_Arn`, `CPU`, `Memory`, `Timestamp`, `Stop_Reason`, `Group`); schema field typing section added.
- `cli/aws-creds.md` — UPDATED: 8 new creds primitives (`Assumption_Id`, `Scope_Name`, `Caller`, `Timestamp`, `Access_Key_Id`, `Session_Token`, `Secret_Access_Key`, `Max_TTL`); schema field typing section added.
- `cli/aws-cloudtrail.md` — UPDATED: 9 new CloudTrail primitives (`Trail_Name`, `Event_Id`, `Event_Time`, `Event_Name`, `Username`, `IP_Address`, `Error_Code`, `Error_Message`, `Json_Blob`); schema field typing section added.
- `cli/aws-s3.md` — UPDATED: 7 new S3 primitives (`Timestamp`, `Content_Type`, `Encryption`, `Version_Id`, `Versioning`, `Prefix`, `Next_Token`); schema field typing section added.
- `cli/aws-observe.md` — UPDATED: 2 new observe primitives (`Source_Name`, `Event_Time`); schema field types updated to show typed annotations.
- `index.md` — UPDATED: version → v0.2.30 (in-progress).

---

## 2026-05-17 PM (v0.2.29 — `sg aws` primitives expansion — Foundation + 8 slices shipped to dev)

Single landing across ~94 commits on `origin/dev` (`ab0c380..759dfaa`). Root `version` bumped to **v0.2.28** (v0.2.29 not yet stamped despite the work-stream label). Source pack: `library/dev_packs/v0.2.29__sg-aws-primitives-expansion/`. Architect reviews under `team/roles/architect/reviews/05/17/v0.2.29__*.md`. Master Dev debrief: `team/claude/debriefs/2026-05-17__v0.2.29-sg-aws-primitives-expansion.md`.

- `cli/aws.md` — NEW: umbrella reality index for `sg aws *`. Documents the shared `aws/_shared/` scaffold (`Mutation__Gate`, `Aws__Tagger`, `Aws__Region__Resolver`, `Aws__Confirm`, `Source__Contract` ABC, shared primitives/schemas/enums).
- `cli/aws-s3.md` — NEW: Slice A. `sg aws s3` — bucket/object lifecycle, `s3 ls/get/put/rm`, signed URLs.
- `cli/aws-ec2.md` — NEW: Slice B. `sg aws ec2` — instance + AMI + key-pair management routed through `Sg__Aws__Session`.
- `cli/aws-fargate.md` — NEW: Slice C. `sg aws fargate` — ECS Fargate cluster / task-definition / task lifecycle.
- `cli/aws-iam-graph.md` — NEW: Slice D. `sg aws iam graph` — IAM relationship graph, role/policy traversal.
- `cli/aws-bedrock.md` — NEW: Slice E. `sg aws bedrock` — `chat`, `agent`, `tool` sub-trees with local-file capture; `check`/`setup` verbs.
- `cli/aws-cloudtrail.md` — NEW: Slice F. `sg aws cloudtrail` — trail listing, event search, JSON export.
- `cli/aws-creds.md` — NEW: Slice G. `sg aws creds` — scoped-credentials surface (REVIEW gate: AppSec sign-off pending).
- `cli/aws-observe.md` — NEW: Slice H. `sg aws observe` — read-only CloudWatch metrics/logs/alarms.
- `cli/index.md` — UPDATED: added rows for all 7 new `cli/aws-*.md` sub-files + the umbrella `cli/aws.md`. Added the v0.2.29 Foundation note.
- `cli/observability.md` — UPDATED: cross-links to the new `aws-observe.md` (note relationship between the legacy `Routes__Observability` and the new read-only CLI).
- `sg-compute/index.md` — UPDATED: notes that `Sg__Aws__Session` now backs all 9 AWS client classes (HCD-1 reshape), `confirm_or_abort` + `--dry-run` wired across mutating verbs (HCD-3).

Significant defects surfaced by Architect reviews and tracked for next session (see `ids/README.md` for new IDs):

- One **CRITICAL regression** during the work-stream (`bcd33439`): Foundation follow-up overwrote Slice B/C/D CLI bodies with `NotImplementedError`. Fixed in `c4cc6ea0`. Worth a hard-won-rule INC.
- **Direct `boto3` usage** has spread across 6 slices and 9 client files (CLAUDE.md rule 13 violation). Architect flagged H-1 as HIGH priority. Tracked as a new INC entry.

---

## 2026-05-17 AM (M-001..M-007 — ontology rollout: reality + catalogue + briefs)

- `reality/` (whole tree) — REFACTOR: full rollout of the ontology proposal §3.4. The 4 flat `v0.1.X__what-exists-today.md` monoliths + `v0.1.31/` migrated to `_archive/`. 9 unmigrated domains (`agent-mitmproxy`, `cli`, `infra`, `lets`, `playwright-service`, `ui`, `qa`, `security`, `vault`) lifted into per-domain `{domain}/index.md` + `proposed/index.md` files. `sg-compute/index.md` (545 lines) split into cover sheet + 6 subarea files (`primitives.md`, `platform.md`, `specs.md`, `cli.md`, `pods.md`, `host-plane.md`) per the 300-line fractal rule. `index.md` Status table refreshed to "11 of 11 migrated"; Migration shim section removed. NEW `verified-by.md` rolling log. Source: ontology proposal at `team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md`.
- `library/catalogue/` — REFACTOR: replaced 9 stale numbered shards with 8 live shards (`index`, `service`, `cli`, `specs`, `infra`, `tests`, `team`, `findings`) using Pattern A naming (stable filenames + frontmatter `as_of:`). First immutable snapshot at `_snapshots/v0.2.25/`. Old shards in `_archive/`.
- `library/docs/specs/` — REFACTOR: `v0.20.55__schema-catalogue-v2.md` (1,439 lines) split into cover sheet + 4 parts; `v0.20.55__routes-catalogue-v2.md` (1,234 lines) split into cover sheet + 4 parts. `═══` H1 banner blocks stripped from these + `v0.20.55__ci-pipeline.md`, replaced with YAML frontmatter per `library/guides/v0.2.15__markdown_doc_style.md`.
- `library/briefing/` → `library/onboarding/` — RENAME: 9 files (M-006a). Distinguishes onboarding sequence from `team/comms/briefs/`. Inbound links updated in `CLAUDE.md`, `library/README.md`, `library/roadmap/phases/v0.1.9__phase-overview.md`.
- `sg_compute/brief/` → `team/comms/briefs/v0.2.25__sg-compute/` — MOVE: 8 files (M-006b). Keeps `sg_compute/` code-only.
- `CLAUDE.md` — FIX: reality-doc pointer now points at `reality/index.md` (not non-existent `v{version}__what-exists-today.md`); canonical version file declared as root `version`; `library/briefing/` references updated to `library/onboarding/`.
- `team/roles/librarian/ids/` — NEW: stable ID registry per ontology proposal §3.3 (`M-NNN` migrations, `INC-NNN` incidents, `B-NNN` backlog). All M-001..M-007 tasks tracked.

Master debrief: this commit batch (six commits: `0556dcc`, `2722cbb`, `277428a`, `7f48cde`, `754aad6`, `1724d95`, `6817f27`, `b62ba53`, `99b5447`, …) plus this changelog entry. Implementation pass for the v0.2.25 ontology rollout. Author: Librarian/Claude. Verified against commits `ce981e5..ab0c380`.

---

## 2026-05-16 (sg aws billing — AWS Cost Explorer CLI sub-package)

- `sg-compute/index.md` — UPDATED: `sgraph_ai_service_playwright__cli/aws/billing/` sub-package added (EXISTS). 4 primitives (`Safe_Decimal__Currency__USD`, `Safe_Str__Aws_Service_Code`, `Safe_Str__Iso8601_Date`, `Safe_Str__Aws_Usage_Type`), 4 enums, 4 schemas, 3 collections, 3 service classes (`Cost_Explorer__AWS__Client`, `Billing__Window__Resolver`, `Billing__Report__Builder`), 6 CLI commands (`last-48h`, `week`, `mtd`, `window`, `summary`, `chart`). `Cli__Aws.py` registers `billing_app`. IAM requirements documented. Branch `claude/plan-billing-view-u0NFG`.

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

## 2026-05-17 (v0.2.25 Phases A–E — credentials multi-role keyring)

- `sg-compute/index.md` — UPDATED: `Keyring__Mac__OS`, `Credentials__Store`, `Audit__Log`, `Sg__Aws__Context`, `Sg__Aws__Session`, `Cli__Credentials`, `Cli__OSX__Keyring`, `Cli__SG__Repl` (now exposes `Cli__SG__Repl` Type_Safe class with `as <role>` pseudo-command) all exist. Phases A–E shipped (keyring backend, standard CLI commands, low-level `sg osx keyring`, REPL `as` + context, STS AssumeRole + cache). 57 new tests; 185 total (no regressions). Phases C/F/G (edit mode, AWS-client migration, transparency banner + correlatable session names + backup/restore) DEFERRED to a v0.2.28 follow-up brief.

---

## 2026-05-17 (v0.2.26 — sg aws lambda extension)

- `sg-compute/index.md` — UPDATED: new `aws/logs/` package (`Logs__AWS__Client`, `Logs__Time__Parser`, `Logs__Insights__Queries`); extended `Lambda__AWS__Client` with `get_function_details`, `invoke`, `list_versions`, `list_aliases`, `list_tags`, `tag_resource`, `untag_resource`, `update_function_configuration`; new services `Lambda__Name__Resolver` (5-tier fuzzy + 5-min cache) and `Lambda__Invocations__Reporter`; new two-level Click hierarchy `Lambda__App__Group` / `Lambda__Function__Group` exposing 12 verbs (`info`, `details`, `config`, `logs`, `invocations`, `invoke`, `deploy`, `delete`, `url`, `tags`, `versions`, `aliases`) + `list`. REPL-navigable: function names appear in `Lambda__App__Group.list_commands()`. Legacy `sg aws lambda deployment {deploy,delete,list}` and `sg aws lambda url {create,show,delete} <name>` kept as deprecation shims (hidden, one-release window). 249 new tests; 265 AWS-CLI total; all 16 pre-existing Lambda tests still pass.

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
