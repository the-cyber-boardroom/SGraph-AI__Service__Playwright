# New Briefs Audit — SG-Compute Migration Direction of Travel

**date** 2026-05-04 22:00 UTC
**from** Audit Agent (Claude Code, this session)
**to** Architect, Librarian, Dev (backend & frontend), Historian
**type** Cross-brief audit / direction-of-travel review
**branch base** dev @ v0.1.169 (in sync with origin)

---

## Why this audit exists

The original v0.1.140 brief trio — `post-fractal-ui__backend`, `post-fractal-ui__frontend`, `sg-compute__migration` — defined a strategic direction (rename to SG/Compute, Node/Pod/Spec/Stack taxonomy, two PyPI packages, ten phases). During execution, the team filed **six additional brief folders** plus three human-authored brief files. This audit maps each new brief against the strategic baseline, identifies extensions / contradictions / supersessions, and recommends what to update or commission next.

---

## Section 1 — Per-brief mini-summary

### 1.1 `team/comms/briefs/v0.1.140__host-control-plane/`

- **Topic** — Build `sgraph_ai_service_playwright__host` package: a privileged FastAPI control plane on every EC2 instance (port 9000, Docker socket access, allowlisted shell, `WS /host/shell/stream`). Adds `host_api_url` + `host_api_key_vault_path` to `Schema__Ec2__Instance__Info`.
- **Audience** — Backend/CLI team + Frontend team (parallel build).
- **Status** — DELIVERED. Backend shipped on `claude/continue-playwright-refactor-xbI4j` (commit 11c2a08) per `03__ref-what-this-session-shipped.md`. The host package was subsequently moved to `sg_compute/host_plane/` in commit c3fc219 (B6 phase). Live today as `sg_compute/host_plane/{fast_api,host,pods,shell}/`.
- **Relation to original** — This is the brief that drove the original `sgraph_ai_service_playwright__host/` work that has since become `sg_compute/host_plane/`. It **predates** and **does not appear in** the migration phase ledger; B6 ("move host plane to `sg_compute/host_plane/`, rename containers→pods") only retrofits the host plane *into* the SG-Compute taxonomy. Verdict: **historical predecessor, now subsumed**. The brief is functionally superseded by the reality of `sg_compute/host_plane/`.
- **Shipped?** — Yes (sgraph_ai_service_playwright__host shipped, then folded into sg_compute/host_plane in B6, commit c3fc219).

### 1.2 `team/comms/briefs/v0.1.140__host-control-plane-ui/`

- **Topic** — UI counterpart to 1.1. Adds Terminal tab + Host API tab to every plugin detail panel; flags Task 0 — `Schema__Stack__Summary` missing `host_api_url` / `host_api_key_vault_path`.
- **Audience** — Frontend session.
- **Status** — DELIVERED. `sp-cli-host-shell` widget + Host API iframe panel are both in flight; subsequent commits (5fc34e5, bf13d62, 8319ffa, 6f14da1) wired the sidecar UI on port 19009 and added Containers/Pods, Boot Log, EC2 Info tabs.
- **Relation to original** — Same as 1.1 — predates the SG-Compute phase ledger, now subsumed. The "stack.host_api_url" coupling point survived the rename to "node".
- **Shipped?** — Yes (host shell widget, iframe Host API panel, Terminal tab); xterm.js Phase-2 interactive shell partially shipped via cookie-based auth in 104566e (resolves the WS auth gap from brief 1.5).

### 1.3 `team/comms/briefs/v0.1.154__sidecar-cors-and-docs-auth/`

- **Topic** — Add CORSMiddleware to `Fast_API__Host__Control` (the host-control-plane image) + `GET /docs-auth?apikey=` endpoint that serves Swagger UI with key pre-injected so the iframe can load same-origin.
- **Audience** — Backend (host control plane / `sg_compute/host_plane/`).
- **Status** — DELIVERED. Commits cfb48cd ("CORS + /docs-auth for host control plane sidecar (v0.1.154)") and b7add3b ("fix(cors): guarantee CORS headers on auth 401 responses from sidecar"). Code present in `sg_compute/host_plane/fast_api/Fast_API__Host__Control.py` (CORSMiddleware as outermost layer) and `Routes__Host__Docs.py` (`/docs-auth` route).
- **What is "sidecar"?** — In this brief the term **"sidecar" is the running `Fast_API__Host__Control` instance on each EC2 node** (port 19009 in this brief; was port 9000 in the original host-control-plane brief — port number drifted during migration). It is the **same image as the host control plane**, just renamed colloquially because it acts as a sidecar to the workload pods on the same node. **Not a third concept.**
- **Relation to original** — **Extends** the host-control-plane brief by closing a CORS gap that wasn't anticipated. Orthogonal to the original SG-Compute migration plan.
- **Shipped?** — Yes.

### 1.4 `team/comms/briefs/v0.1.154__sidecar-enhancements-for-ui/`

- **Topic** — Three new endpoints on the sidecar: `GET /host/logs/boot` (cloud-init tail), `GET /containers/{name}/logs` (pod log tail), `GET /containers/{name}/stats` (point-in-time CPU/mem snapshot).
- **Audience** — Backend (host control plane).
- **Status** — DELIVERED. Commits e22c606 ("Sidecar UI endpoints: boot log, pod logs (updated schema), pod stats"), c3fc219 ("B6: move host plane to sg_compute/host_plane/, rename containers→pods"), 40bb631 ("sidecar: add /containers/* routes for UI panel"), c3e8ffd ("nodes-view: add Boot Log tab wired to GET /host/logs/boot").
- **"Sidecar"** — Same usage as 1.3: the `Fast_API__Host__Control` running on each node. Same instance that the host-control-plane brief commissioned.
- **Relation to original** — **Extends** the host-control-plane API surface; orthogonal to the migration phase ledger; aligned with the B6 containers→pods rename (the brief still uses `containers` in URLs but the underlying handlers are pod-oriented).
- **Shipped?** — Yes.

### 1.5 `team/comms/briefs/v0.1.154__ws-shell-stream-auth/`

- **Topic** — Browsers cannot send `X-API-Key` headers during WS upgrade. The `_Middleware` rejects with 1006. Proposes Option A (query param fallback `?api_key=`) or Option B (per-handler validation).
- **Audience** — Backend (host control plane sidecar).
- **Status** — DELIVERED via different mechanism. The brief proposed `?api_key=` query-param fallback; the team instead landed **cookie-based auth** in commit 104566e ("sidecar: cookie-based auth + iframe terminal (same pattern as Host API tab)"). This is a Pattern C that wasn't in the brief — uses `/auth/set-cookie-form` + `/auth/set-auth-cookie` flow (visible in `_AUTH_FREE_PATHS` in `Fast_API__Host__Control.py`). Subsequent fix in 9fffdee ("fix(shell): fix JS syntax error in shell page + inline auth in terminal tab").
- **P-1 status** — Yes, this is the WS-shell hardening flagged as P-1 in earlier reality docs. Resolved by cookie auth, not query-param auth.
- **Relation to original** — **Refines** host-control-plane brief Task 3 (which simply specified `WS /host/shell/stream`). The host-control-plane brief did not anticipate the browser-WS-header constraint.
- **Shipped?** — Yes, via cookie-based auth (different from the proposed Option A/B).

### 1.6 `team/comms/briefs/v0.1.162__s3-storage-node/`

- **Topic** — Brand-new node spec `sg_compute_specs/s3_server/` — a boto3-transparent S3-compatible storage node. Two-layer split: `sg_compute_specs/s3_server/` (the spec) + `sg_s3_server/` (HTTP/SigV4/XML implementation, separate package). Four operation modes (FULL_LOCAL, FULL_PROXY, HYBRID, SELECTIVE). Adds `OBJECT_STORAGE` to `Enum__Spec__Capability`. Phase 1 = FULL_PROXY + call log.
- **Audience** — Architect + Dev (handover indicates a new repo `SG-Compute/SG-Compute__Spec__Storage-S3` will own implementation; spec-layer work stays in the Playwright repo).
- **Status** — PROPOSED. Brief landed in commit a8abf1b; handover landed in commit 063d7e9. No spec folder `sg_compute_specs/s3_server/` exists yet — the spec is not yet implemented.
- **Relation to original** — **New direction not in any original brief.** The migration phase ledger (B1-B8) lists existing specs (docker, ollama, opensearch, podman, vnc, neko, prometheus, elastic, firefox, mitmproxy, playwright) — `s3_server` is a wholly new spec category and the **first storage-class spec**.
- **Shipped?** — No. Architecture brief + dev brief + Memory-FS Q&A complete; no implementation yet.

### 1.7 `team/humans/dinis_cruz/briefs/05/04/Storage_FS__S3.py`

- **Topic** — Working Python implementation of `Storage_FS__S3`, a Memory-FS `Storage_FS` adapter that uses `osbot_aws.aws.s3.S3` for the storage layer (file__bytes, file__save, file__exists, etc., plus presigned URLs and versioning helpers).
- **Audience** — Dev implementing the S3 storage node Phase 2.
- **Status** — REFERENCE / PROPOSED. Not committed into the repo as production code (only sits in `team/humans/dinis_cruz/briefs/05/04/`).
- **Relation to original** — **Memory-FS integration seam** — populates the abstract `S3__Backend` interface from brief 1.6 §5.
- **Shipped?** — No (this is reference code; not in `sg_compute_specs/s3_server/`).

### 1.8 `team/humans/dinis_cruz/briefs/05/04/memory-fs-integration-response.md`

- **Topic** — Response from the Memory-FS team. Confirms package name `memory-fs`, import path `from memory_fs import Memory_FS`, the `Storage_FS` interface (`file__save`, `file__bytes`, `file__metadata`, `file__delete`, `files__paths`, etc.), and S3-operation-to-Storage_FS mapping. Includes complete adapter code.
- **Audience** — Dev implementing the S3 storage node.
- **Status** — REFERENCE / DELIVERED (as documentation).
- **Relation to original** — Answers the open question in brief 1.6 §1 ("What Python package name does Memory-FS expose?"). Unblocks Phase 2.
- **Shipped?** — N/A (it's a Q&A document; the implementation it unblocks has not shipped).

### 1.9 `team/humans/dinis_cruz/briefs/05/04/v0.27.2__arch-brief__s3-compatible-api-full-boto3-transparency.md`

- **Topic** — The original human arch brief. Articulates the non-negotiable: a boto3 client pointed at `endpoint_url` must have **zero idea** it's not real AWS S3. SigV4, XML responses, error formats, edge cases, plus a discovery-first call log so the team only implements APIs that real consumers (Memory-FS, osbot-aws, SGit, Cyber Boardroom) actually call.
- **Audience** — Architect (lead), Dev.
- **Status** — REFERENCE — this is the parent brief that brief 1.6 implements.
- **Relation to original** — **Wholly orthogonal to the SG-Compute migration plan.** Introduces a new theme (S3-compatible API surface, AWS-transparency mocking, call-log discovery) that the original strategic briefs never anticipated.
- **Shipped?** — No (call log + S3 server is at brief stage).

---

## Section 2 — Direction-of-travel mapping

The original direction:

1. Refactor codebase into `sg_compute` SDK + `sg_compute_specs` catalogue.
2. Node / Pod / Spec / Stack taxonomy.
3. Eight backend phases (B1-B8) + ten frontend phases (F1-F10).
4. Eventually publish to PyPI.

The new briefs reveal **five emergent themes that were not in the original migration plan**:

### Theme A — The host-plane / sidecar pattern as a first-class concept

The original `01__architecture.md` mentions `host_plane` only briefly ("`host_plane` FastAPI on port 9000"). The host-control-plane briefs (1.1, 1.2) and the sidecar enhancement briefs (1.3, 1.4) reveal a **fully-fledged sidecar architecture** with its own:

- Auth model (X-API-Key + cookie + WS query-param fallback)
- CORS contract (CORSMiddleware as outermost layer; CORS guaranteed even on auth 401)
- Iframe-friendly Swagger (`/docs-auth`)
- Boot log endpoint (`/host/logs/boot`)
- Container/pod logs and stats
- WS shell with cookie auth (the original "rbash" plan from 1.1 was superseded)

This is a **vocabulary the original briefs do not capture**. The original B6 phase entry says merely "move host plane; rename containers → pods" — it doesn't acknowledge that the host plane gained its own auth pattern, CORS layer, sidecar nickname, and a UI panel ecosystem.

### Theme B — S3-compatible API & call-log discovery

Brief 1.9 introduces a discovery-first methodology (log every call, build only what's used) and the goal of full boto3 transparency. Neither concept appears in the original migration plan. Brief 1.6 then realises this as a node spec, adding `OBJECT_STORAGE` capability to the spec taxonomy.

### Theme C — Memory-FS integration

The migration plan never mentioned Memory-FS. Briefs 1.7 and 1.8 introduce Memory-FS as an external dependency the SG-Compute storage specs will leverage, and confirm `memory-fs` as a separate PyPI package the SDK plans to consume.

### Theme D — Cross-repo handover (a new repo for one spec)

Brief 1.6's `04__new-session-handover.md` directs implementation to a brand-new repo `SG-Compute/SG-Compute__Spec__Storage-S3`. The original migration plan stayed in `the-cyber-boardroom/SGraph-AI__Service__Playwright` and only revisited extraction "after phase 8". Brief 1.6 implicitly **extracts a single spec to its own repo before the global extraction phase**.

### Theme E — Operation-mode taxonomy for specs

Brief 1.6's four-mode taxonomy (FULL_LOCAL / FULL_PROXY / HYBRID / SELECTIVE) is generally useful — a Firefox spec could ship a real / proxied / mock mode similarly. The original spec contract in `01__architecture.md` did not define a mode dimension.

### Whether these themes need to be reflected in the original briefs

| Theme | Reflect in originals? |
|-------|-----------------------|
| A — Sidecar / host plane | **YES** — update `01__architecture.md` §3 (platforms layer) and `30__migration-phases.md` B6 to reference the sidecar contract (CORS, cookie auth, /docs-auth). |
| B — S3-compatible API | **YES** — add an §8 "Storage specs" section to `01__architecture.md`. The OBJECT_STORAGE capability is a new spec-taxonomy axis that affects every future spec. |
| C — Memory-FS | **PARTIAL** — only as a dependency note in storage-related specs. Don't bake into the SDK contract. |
| D — Cross-repo extraction (S3 spec to its own repo) | **YES — flag for review.** This contradicts the "stay in this repo until phase 8" rule from the migration `00__README.md` Out-of-scope section. The Architect should explicitly decide if S3 is the exception or the new pattern. |
| E — Operation-mode taxonomy | **MAYBE** — propose as an Architect review topic; do not amend the spec contract until validated against ≥2 specs. |

---

## Section 3 — Brief-level gap analysis

### Contradictions (briefs that disagree)

| New brief | Contradicts | Detail |
|-----------|-------------|--------|
| 1.5 (ws-shell-stream-auth) ships **cookie-based auth** | Host-control-plane brief 1.1 specified `/bin/rbash` + `X-API-Key` only | The auth model evolved beyond `X-API-Key` into a multi-mode (header + cookie + same-origin iframe). The original brief never anticipated browsers' WS-header limitation. |
| 1.6 (s3-storage-node) directs work to **a new repo `SG-Compute/SG-Compute__Spec__Storage-S3`** | sg-compute migration `00__README.md` Out-of-scope: "Repo extraction. Not in this phase. After phase 8 we revisit" | Brief 1.6 starts cross-repo work *before* phase 8. Worth an explicit decision. |
| Sidecar port is **19009** in 1.3, 1.4, 1.5 | Original host-control-plane brief specified **port 9000** | Port number drifted; reality docs and any external user-data scripts may be inconsistent. Worth a librarian sweep. |

### Extensions (additive, no conflict)

| New brief | Extends |
|-----------|---------|
| 1.3 (sidecar CORS + /docs-auth) | Host-control-plane Task 3 — adds CORSMiddleware + `/docs-auth` endpoint |
| 1.4 (sidecar enhancements) | Host-control-plane API surface — adds `/host/logs/boot`, pod logs, pod stats |
| 1.5 (ws-shell-stream-auth) | Host-control-plane Task 3 (WS handler) — adds auth model |
| 1.6 (s3-storage-node) | sg-compute migration B3.x phase ledger — adds a new storage-class spec |
| 1.7, 1.8 (Memory-FS) | Brief 1.6 §5 storage backend seam |

### Did the team ship something different from `04__vault-write-contract.md` (the original backend brief 04)?

Reviewed git log — no commits matching `vault.*plugin.*write` or `vault.*receipt`. The vault-write contract appears **not yet shipped**. The firefox configuration column (which would be the first consumer) also has no commits matching. **Status of vault-write contract: still PROPOSED, not contradicted, not yet built.** The team prioritised host-plane/sidecar/S3 work over the original vault-write item.

---

## Section 4 — Briefs that need updating

### `v0.1.140__sg-compute__migration/01__architecture.md`

- **Still 100% correct?** No.
- **Sections needing change:**
  - §1 Taxonomy — add explicit mention that **every Node runs a sidecar (`sg_compute/host_plane/`)** with the documented auth contract (X-API-Key + cookie + WS); the sidecar is part of the Node abstraction, not an afterthought.
  - §3 Platforms layer / §4 Spec contract — add an `OBJECT_STORAGE` capability example and reference the storage-spec pattern (with Memory-FS seam).
  - §6 Legacy mapping — reflect that `sgraph_ai_service_playwright__host` already migrated to `sg_compute/host_plane/` (commit c3fc219, B6 closed).
- **Recommendation** — **Amend in place** with a "Living updates" appendix dated 2026-05-04 that captures the sidecar contract, the OBJECT_STORAGE capability, and Memory-FS dependency. Do not rewrite the body — the body is still the strategic baseline.

### `v0.1.140__sg-compute__migration/30__migration-phases.md`

- **Still 100% correct?** No.
- **Sections needing change:**
  - The phase ledger should mark B6 as **DONE** (commit c3fc219).
  - B6 exit criteria should include "sidecar gains CORS, /docs-auth, cookie-auth, boot-log/pod-logs/pod-stats endpoints" — none of which are listed.
  - B7.A is also DONE (commit 665a308) and B7.B is DONE (commit 1c9cdb2). Brief still says "session 10".
  - B8 is partially DONE (commit b1f810a "B8: PyPI build setup").
  - Add a B3.x slot for `s3_server` spec migration (it is not in any current B3.x line because it's a new spec, not a migration).
- **Recommendation** — **Amend in place** by appending a "Status as of 2026-05-04" column to the phase ledger.

### `v0.1.140__sg-compute__migration/10__backend-plan.md` (not read in detail in this audit)

- Likely needs the same status update (mark closed phases done; flag s3_server as a new spec). Recommend Architect review.

### `v0.1.140__post-fractal-ui__backend/04__vault-write-contract.md`

- **Still 100% correct?** Yes — no contradicting work has shipped.
- But **firefox is no longer the first consumer in practice**: the sidecar-cookie auth (briefs 1.5, 1.3) and the S3 server's call log persistence (brief 1.6) are now competing first consumers. Re-evaluate whether the vault-write contract should be designed for blob-and-credential traffic from the sidecar/S3 paths, not just firefox secrets.
- **Recommendation** — **Hold and re-scope.** Architect to decide whether to broaden the contract to cover sidecar-issued vault writes (boot artefacts, call-log archives) before any consumer ships.

### `v0.1.140__post-fractal-ui__backend/01__plugin-manifest-endpoint.md`

- **Likely outdated** — by v0.1.169 the `Plugin__Registry` has been replaced by `Spec__Loader` per migration plan B2. The brief was written before "plugin → spec" rename closed. Verify against current `Spec__Loader` then either close as DELIVERED or amend the schema names from `Plugin__*` to `Spec__*`.
- **Recommendation** — **Amend with a "renamed terms" footnote** OR mark superseded by the SG-Compute spec contract.

### `v0.1.140__host-control-plane/` (entire folder)

- **Still 100% correct?** Mostly yes for archaeological purposes; **functionally superseded** by the realisation `sg_compute/host_plane/` plus briefs 1.3 / 1.4 / 1.5 which extend the original API surface.
- **Recommendation** — **Move to `team/comms/briefs/archive/v0.1.140__host-control-plane__c3fc219/`** with a banner pointer to `sg_compute/host_plane/` and to briefs 1.3 / 1.4 / 1.5.

### `v0.1.140__host-control-plane-ui/`

- **Recommendation** — **Archive** with a pointer to the current `sp-cli-host-shell` / `sp-cli-nodes-view` components on `dev`.

---

## Section 5 — Briefs that need to be ADDED

Based on the direction of travel, the following NEW briefs should be commissioned:

### 5.1 — Sidecar Architecture spec (P-1)

- **Why** — "Sidecar" is now a first-class concept across briefs 1.3 / 1.4 / 1.5, but no single document defines the sidecar contract (auth modes, CORS, port, /docs-auth, /auth/set-cookie-form, boot-log, pod-logs/stats, WS shell, allowlist).
- **Suggested path** — `library/docs/specs/v0.1.169__sidecar-architecture.md` and a brief `team/comms/briefs/v0.1.169__sidecar-contract/`.
- **Owner** — Architect.

### 5.2 — Storage Spec category (P-2)

- **Why** — `OBJECT_STORAGE` capability is a new axis. We need an Architect-level decision on what makes a "storage spec", what the common interface is (Memory-FS `Storage_FS` adapter? S3 backend interface? Both?), and what the Stack-level composition rules are when a workload spec depends on a storage spec.
- **Suggested path** — `team/comms/briefs/v0.1.169__storage-spec-category/` with sections for `s3_server`, future `vault_blob`, future `local_fs`.
- **Owner** — Architect + Dev (Storage-S3 session lead).

### 5.3 — Cross-repo extraction policy (P-1, blocks brief 1.6)

- **Why** — Brief 1.6's handover directs `s3_server` implementation to a new repo `SG-Compute/SG-Compute__Spec__Storage-S3` *before* phase 8 of the migration. The original `00__README.md` Out-of-scope section explicitly defers repo extraction. Architect must choose: (a) S3 is a one-off exception; (b) every new spec gets its own repo from day one; (c) brief 1.6 is in error and S3 stays here until phase 8.
- **Suggested path** — `team/comms/briefs/v0.1.169__spec-repo-extraction-policy/`.
- **Owner** — Architect (decision-only brief).

### 5.4 — Operation-mode taxonomy (P-3)

- **Why** — Brief 1.6 introduces FULL_LOCAL / FULL_PROXY / HYBRID / SELECTIVE for one spec. If the pattern generalises (Firefox could have these; Elastic too), it belongs in the SDK, not in one spec. If not, it stays spec-local. Architect call needed.
- **Suggested path** — `team/comms/briefs/v0.1.169__spec-operation-modes/`.
- **Owner** — Architect.

### 5.5 — Call-log persistence contract (P-3)

- **Why** — Brief 1.9 mandates a discovery-first call log. Where do those logs live? In-process? Memory-FS? CloudWatch? S3 (recursive)? If they go to a vault, they touch the vault-write contract from `post-fractal-ui__backend/04`.
- **Suggested path** — `team/comms/briefs/v0.1.169__call-log-persistence/`.
- **Owner** — Architect + Dev.

### 5.6 — Sidecar↔SP-CLI catalog ownership boundary (P-2)

- **Why** — Commit 1c96fbe ("ec2-info: move to SP CLI catalog (has IAM) — remove from sidecar (no IAM)") reveals an in-flight design conversation: which routes belong on the sidecar (no IAM) vs the management plane (has IAM)? This is a fundamental architectural decision that should be a written contract, not folklore in commit messages.
- **Suggested path** — `team/comms/briefs/v0.1.169__sidecar-vs-control-plane-boundary/`.
- **Owner** — Architect.

### 5.7 — Host-plane port stabilisation (P-3, low risk)

- **Why** — Port drift: original brief said 9000, sidecar briefs say 19009. Pick one, document it, sweep references in user-data scripts, reality docs, UI defaults.
- **Suggested path** — Could be a librarian "convention sweep" rather than a brief; but worth surfacing.
- **Owner** — Librarian.

---

## Appendix — Verification commits

Commits referenced in this audit (for traceability):

| Commit | Subject | Section |
|--------|---------|---------|
| c3fc219 | B6: move host plane to sg_compute/host_plane/, rename containers→pods | 1.1, 1.4, S4 |
| cfb48cd | CORS + /docs-auth for host control plane sidecar (v0.1.154) | 1.3 |
| b7add3b | fix(cors): guarantee CORS headers on auth 401 responses from sidecar | 1.3 |
| 40bb631 | sidecar: add /containers/* routes for UI panel (v0.1.154 brief) | 1.4 |
| e22c606 | Sidecar UI endpoints: boot log, pod logs (updated schema), pod stats | 1.4 |
| c3e8ffd | nodes-view: add Boot Log tab wired to GET /host/logs/boot | 1.4 |
| 104566e | sidecar: cookie-based auth + iframe terminal | 1.5 |
| 9fffdee | fix(shell): fix JS syntax error in shell page + inline auth in terminal tab | 1.5 |
| 1c96fbe | ec2-info: move to SP CLI catalog (has IAM) — remove from sidecar (no IAM) | S5.6 |
| 6f14da1 | nodes-view: fix CORS on PENDING nodes + add EC2 Info tab | 1.2 |
| 5fc34e5 | Wire host control plane sidecar (port 19009) to nodes UI | 1.2 |
| a8abf1b | feat: add v0.1.162 S3 Storage Node Spec brief (3 files) | 1.6 |
| dee4725 | docs: add Memory-FS integration questions for S3 storage node | 1.6, 1.8 |
| 063d7e9 | docs: add new-session handover for SG-Compute__Spec__Storage-S3 | 1.6, S3 (D) |
| b1f810a | B8: PyPI build setup — sg-compute and sg-compute-specs wheels | S4 |
| 665a308 | B7.A: move agent_mitmproxy → sg_compute_specs/mitmproxy/ | S4 |
| 1c9cdb2 | B7.B: fold sgraph_ai_service_playwright → sg_compute_specs/playwright/core/ | S4 |
| 8319ffa | Phase 3/5: docker sidecar, node list/create/delete CLI, EC2 platform fix | 1.2 |

End of audit.
