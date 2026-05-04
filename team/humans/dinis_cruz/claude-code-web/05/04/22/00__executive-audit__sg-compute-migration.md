# Executive Audit — SG/Compute Migration v0.1.140 → v0.1.169

**Date:** 2026-05-04
**Branch base:** `dev` @ v0.1.169 (HEAD `5483738`)
**Audited briefs:** `team/comms/briefs/v0.1.140__sg-compute__migration/` + `…__post-fractal-ui__backend/` + `…__post-fractal-ui__frontend/`
**Detail audits (companion files in this folder):**
- [`backend-audit__sg-compute-migration.md`](backend-audit__sg-compute-migration.md) (257 lines)
- [`frontend-audit__sg-compute-and-post-fractal-ui.md`](frontend-audit__sg-compute-and-post-fractal-ui.md) (119 lines)
- [`new-briefs-audit__sg-compute.md`](new-briefs-audit__sg-compute.md) (295 lines)

---

## TL;DR

In **two days** the team executed almost the entire critical path of an 18-phase migration. **8 of the 9 specs migrated**, the SDK exists on PyPI shape, both wheels build, the host plane moved, the Playwright service and agent_mitmproxy are folded in. The taxonomy (Node/Pod/Spec/Stack) is cemented in code.

But the speed came with three high-leverage failures, all of which must be closed before the dashboard can be repointed at the new control plane:

1. **B4 control plane is a façade.** Endpoints exist but `Routes__Compute__Nodes` returns a hard-coded empty list; `Pod__Manager` and `Stack__Manager` never built; no Lambda handler; no `/legacy/` mount. The dashboard cannot create, list, or delete a node via the new control plane.
2. **`linux` spec was silently dropped** (B3.1 in the brief). Every spec has `extends=[]` instead of `extends=['linux']`. The fractal-composition story has no base.
3. **B7.A, B7.B, B6 were copies, not moves.** `agent_mitmproxy/`, `sgraph_ai_service_playwright/`, and `sgraph_ai_service_playwright__host/` all still exist at the repo root with full original code. **Five trees in dual-write state** (these three plus all 8 B3 legacy spec dirs). Drift risk is real and will compound.

In parallel, **5 strategic themes emerged** that the original briefs did not anticipate. The biggest is the **sidecar pattern** — what was a single sentence ("`host_plane` FastAPI on port 9000") in the original architecture has grown into a full sub-architecture with auth modes (X-API-Key / cookie / WS query-param), CORS contract, iframe-friendly Swagger, boot log + pod log + pod stats endpoints. None of this is captured in the strategic briefs the dev teams are still following.

The frontend team did good work on what was unblocked (F1 ✅, F4 ⚠ entity-half done, F7 ✅, F8 ✅ — and the entire host-control-plane / sidecar / nodes-view track shipped from a chain of new briefs). The strategically important phases (F2 API client, F3 Specs view, F5 catalogue loader, F6 per-spec UI co-location) are all backend-blocked on the B4 façade.

**My recommendation:** before commissioning more direction-of-travel work, the team owes itself **one focused gap-closure session per team** — backend closes B4 + linux + per-spec CLI + B7 cleanup; frontend closes F4 per-type namespace + decision-only docs. Then the briefs need updating to reflect the 5 emergent themes, and 3 new P-1 briefs should be commissioned (Sidecar Architecture, Cross-repo Extraction Policy, Backend Gap Closure).

---

## 1. What was delivered (status table)

### Backend phases (sg-compute migration)

| Phase | Topic | Status | Notes |
|-------|-------|--------|-------|
| B1 | Rename `ephemeral_ec2/` → `sg_compute/`; add `sg_compute_specs/` | ✅ DONE | `sg_compute__tests/stacks/` cosmetic leftover only |
| B2 | Foundations (primitives, enums, schemas, platforms, Spec__Loader, Spec__Resolver, Node__Manager) | ✅ DONE | `Pod__Manager` and `Stack__Manager` not built (deferred without flagging) |
| B3.0 | docker spec | ✅ DONE | Layout uses `service/` not `core/`; no `cli/`; no shim |
| B3.1 | **linux** spec (the fractal composition base) | ❌ **DROPPED** | Team renumbered everything down by one; `linux` was silently skipped |
| B3.1 | podman spec | ✅ DONE | Renumbered from B3.2 |
| B3.2 | vnc spec | ✅ DONE | Renumbered from B3.3 |
| B3.3 | neko spec | ✅ DONE | Renumbered from B3.4 |
| B3.4 | prometheus spec | ✅ DONE | Renumbered from B3.5 |
| B3.5 | opensearch spec | ✅ DONE | Renumbered from B3.6 |
| B3.6 | elastic spec | ✅ DONE | Renumbered from B3.7 |
| B3.7 | firefox spec | ✅ DONE | Brief had this as B3.8 — same off-by-one as the linux drop |
| B4 | Control plane FastAPI | ⚠ **FAÇADE** | Endpoints exist but routes return placeholders; `Node__Manager` never wired; no `/legacy/` mount; no Lambda handler; no `Routes__Compute__Pods.py` at all |
| B5 | `sg-compute` CLI | ⚠ PARTIAL | Root verbs wired; per-spec dispatcher missing (depends on B3 `cli/` move); `validate` verb missing |
| B6 | Move host plane; rename containers→pods | ⚠ DUAL-WRITE | Code at new path; legacy `sgraph_ai_service_playwright__host/` not deleted; `Routes__Host__Containers` retained as alias |
| B7.A | `agent_mitmproxy/` → `sg_compute_specs/mitmproxy/` | ⚠ DUAL-WRITE | Copy not move; legacy `agent_mitmproxy/` still at repo root |
| B7.B | `sgraph_ai_service_playwright/` → `sg_compute_specs/playwright/core/` | ⚠ DUAL-WRITE | Copy not move; explicit in the commit body — kept legacy "for backward-compat with `__cli/`" |
| B8 | PyPI build setup | ✅ DONE | Both wheels build, `pip install` smoke passes, entry-points work |

**Score: 11 ✅ · 4 ⚠ · 1 ❌ · 18 phase items.**

### Frontend phases (sg-compute migration)

| Phase | Topic | Status | Notes |
|-------|-------|--------|-------|
| F1 | Terminology label sweep | ✅ DONE | One residual: `sp-cli-launch-panel.js:46` "Stack name is required" |
| F2 | API client migration to `/api/{nodes,specs,pods,stacks}` + feature flag | ❌ NOT STARTED | Backend-blocked on B4 façade |
| F3 | Specs view (left-nav item + browse pane) | ❌ NOT STARTED | Backend-blocked |
| F4 | Wire-event vocabulary `stack.*`→`node.*` | ⚠ PARTIAL | Entity events done with deprecated aliases; per-type namespace `plugin:firefox.*` → `spec:firefox.*` not migrated |
| F5 | Catalogue loader (drop `PLUGIN_ORDER`) | ❌ NOT STARTED | `PLUGIN_ORDER` still at `sp-cli-launcher-pane.js:4`; static catalogue moved into `sp-cli-compute-view.js` (a sideways step) |
| F6 | Per-spec UI co-location at `sg_compute_specs/<name>/ui/` | ❌ NOT STARTED | All UI still under `__api_site/plugins/<name>/` |
| F7 | Stacks placeholder view | ✅ DONE | `sp-cli-stacks-view` renders "Coming soon" |
| F8 | Host-plane URL update `/containers/*` → `/pods/*` | ✅ DONE | All `/pods/*` in `nodes-view`; landed via the sidecar track |
| F9 | Cosmetic `sp-cli-*` → `sg-compute-*` rename | DEFERRED | Correct deferral |
| F10 | Move dashboard to `sg_compute/frontend/` | DEFERRED | Correct deferral |

**Score: 4 ✅ · 1 ⚠ · 4 ❌ · 2 DEFERRED.** F2/F3/F5/F6 are all backend-blocked.

### Post-fractal-UI brief items

| Item | Topic | Status | Notes |
|------|-------|--------|-------|
| BE-01 | Plugin manifest endpoint | ⚠ Renamed | `Spec__Loader` replaces `Plugin__Registry`. Brief is stale on names. |
| BE-02 | Stack-creation payload — three modes | ❌ Not shipped | No `creation_mode`/`ami_id`/`instance_size` payload yet |
| BE-03 | Firefox configuration endpoints | ❌ Not shipped | |
| BE-04 | Per-plugin vault-write contract | ❌ Not shipped | First-consumer story changed (sidecar / S3 now competing) |
| FE-01 | Manifest loader (UI side) | ❌ Not started | Same as F5 |
| FE-02 | Launch flow three modes | ❌ Not started | Backend-blocked |
| FE-03 | Firefox 5-panel configuration column | ❌ Not started | Backend-blocked |
| FE-04.1 | linux→podman rename residue | ✅ DONE | All 9 sites swept |
| FE-04.2 | Remove deprecated components | ✅ DONE | All 4 deleted |
| FE-04.3 | Embed `<sg-remote-browser>` in elastic/prometheus/opensearch | ✅ DONE | |
| FE-04.4 | Card label vs provider consistency (firefox) | ⚠ Not verified | Cheap follow-up |
| FE-04.5 | Plugin-folder structure decision | ❌ Not filed | UI Architect role-folder doesn't exist |
| FE-05.1-6 | Governance decisions (firefox/api blessing, event vocab spec, vault-optional, …) | ❌ All open | Decision-only items, none filed |

---

## 2. The 6 critical gaps

| # | Gap | Impact | Owner |
|---|-----|--------|-------|
| **G1** | **`linux` spec missing**; every spec has `extends=[]` instead of `extends=['linux']` | Fractal composition base (B3.1's marquee feature) doesn't exist; defeats the brief's promise that "firefox extends [docker, linux]" | Backend |
| **G2** | **B4 control plane is a façade.** `Routes__Compute__Nodes.list_nodes` returns hard-coded `{nodes: [], total: 0}`; no POST/GET-by-id/DELETE; no `Routes__Compute__Pods` at all; no `/legacy/` mount; no Lambda handler | Dashboard cannot run lifecycle ops via the new surface — the front-end team's F2/F3/F5 phases are blocked | Backend |
| **G3** | **No per-spec `cli/` subdirectory.** Brief required `sg_compute_specs/<spec>/cli/` for every spec; team folded everything into `service/`. B5's `sg-compute spec docker create` dispatcher cannot work | The CLI's marquee feature is non-functional | Backend |
| **G4** | **Five trees in dual-write state.** `sgraph_ai_service_playwright/`, `sgraph_ai_service_playwright__host/`, `agent_mitmproxy/`, plus 8 `__cli/<spec>/` directories — all still contain full original code, not deprecation shims | Drift risk; CI may run against either path; cleanup is unbounded effort the longer it waits | Backend |
| **G5** | **`Enum__Spec__Capability` set was never Architect-locked.** Header in `sg_compute/primitives/enums/Enum__Spec__Capability.py:5-22` still says "Architect locks set before phase 3" | Specs are declaring capabilities against an unsanctioned vocabulary | Architect |
| **G6** | **F4 per-type namespace not migrated.** `sp-cli:plugin:firefox.*` → `sp-cli:spec:firefox.*` not done in emitters or `admin.js:102` listener | Vocabulary alignment is half-done; events log will mix "plugin" + "node" forever | Frontend |

G2 is the single highest-leverage item — its closure unblocks four frontend phases.

---

## 3. Direction of travel: 5 emergent themes (not in original briefs)

### A. Sidecar / host-plane is now first-class

The original architecture had `host_plane/` as a single bullet. Reality at v0.1.169:

- **Auth model**: X-API-Key + cookie (`/auth/set-cookie-form` + `/auth/set-auth-cookie`) + WS shell uses cookie-based auth (Pattern C — neither Option A nor B from `v0.1.154__ws-shell-stream-auth/`).
- **CORS contract**: `CORSMiddleware` as outermost layer; CORS guaranteed even on auth 401.
- **Iframe-friendly Swagger**: `/docs-auth?apikey=` injects key for same-origin iframe load.
- **API surface**: `/host/logs/boot`, `/containers/{name}/logs`, `/containers/{name}/stats`, `/host/status`, `/host/runtime`, `/pods/*`, plus shell exec + WS shell stream.
- **Port drift**: brief 1.1 said `:9000`; v0.1.154 briefs use `:19009`. User-data and reality docs may be inconsistent.

This sub-architecture deserves its own contract spec.

### B. S3-compatible API + full boto3 transparency

Brief `v0.27.2__arch-brief__s3-compatible-api-full-boto3-transparency.md` introduces a discovery-first methodology (log every call, build only what's used) and the ambition that `boto3.client('s3', endpoint_url=...)` cannot tell it isn't real AWS. Brief `v0.1.162__s3-storage-node/` realises this as a Spec, adding `OBJECT_STORAGE` to `Enum__Spec__Capability`. **Wholly new direction; first storage-class spec in the catalogue.**

### C. Memory-FS as an external dependency

Brief `Storage_FS__S3.py` + `memory-fs-integration-response.md` confirm `memory-fs` as a separate PyPI package the storage specs will depend on (`pip install memory-fs`, `from memory_fs import Memory_FS`). Not in the original SDK plan.

### D. Cross-repo extraction (a single spec moves to its own repo)

Brief 1.6's handover at `04__new-session-handover.md` directs `s3_server` implementation to a brand-new repo `SG-Compute/SG-Compute__Spec__Storage-S3`. **This contradicts** the migration `00__README.md`'s explicit "Repo extraction. Not in this phase. After phase 8 we revisit." The Architect must rule: is S3 a one-off exception, or is it the new pattern?

### E. Operation-mode taxonomy for specs

Brief 1.6 introduces `FULL_LOCAL / FULL_PROXY / HYBRID / SELECTIVE` for one spec. Could generalise (Firefox might want real / proxied / mock; Elastic too). Spec contract doesn't have a mode dimension yet. Architect call.

---

## 4. What still needs to be done

### 4.1 Highest priority — backend gap-closure

A single PR (or small sequence) by the backend team to close G1-G5. Specifically:

- **Migrate `linux` as a spec** (B3.1 redo). Add `extends=['linux']` to every dependent spec's manifest after.
- **Wire `Routes__Compute__Nodes` to `Node__Manager`**. Implement POST / GET-by-id / DELETE. Build `Pod__Manager`, `Routes__Compute__Pods`. Build `Stack__Manager` placeholder.
- **Add Lambda handler at `sg_compute/control_plane/lambda_handler.py`**.
- **Add `/legacy/` mount** for `Fast_API__SP__CLI` backwards-compat.
- **Add per-spec `cli/` directories** for all 8 migrated specs. Wire `sg-compute spec <id> <verb>` dispatcher in `Cli__Compute__Spec.py`.
- **Add `sg-compute spec validate`** verb.
- **Architect locks `Enum__Spec__Capability`** closed set; remove the "to be locked" header comment.
- **Cleanup discipline**: convert legacy paths (`sgraph_ai_service_playwright__host`, `agent_mitmproxy`, all 8 `__cli/<spec>/` dirs) to deprecation-warning re-export shims. Goal: no legacy path runs original code; everything proxies to the new location.

This is one focused brief: I'd commission `team/comms/briefs/v0.1.169__sg-compute-gap-closure/`.

### 4.2 Second priority — frontend follow-up

Once G2 closes, F2/F3/F5/F6 unblock. Suggested order:

- **F2 API client migration** + field renames (`stack_id`→`node_id`, `type_id`→`spec_id`, `container_count`→`pod_count`, `stack_name`→`node_name`).
- **F5 catalogue loader** (consumer of `GET /api/specs` from B4-fixed control plane). Replaces `PLUGIN_ORDER`.
- **F3 Specs view** (consumer of the same).
- **F4 per-type namespace finish** (`sp-cli:plugin:*` → `sp-cli:spec:*` with deprecated aliases).
- **F6 per-spec UI co-location** — gradual, one spec per session.

Decision-only items (FE-04.5, FE-05.1-6) can land at any time; nothing blocks them.

### 4.3 Third priority — direction-of-travel work

Once gap closure is done:

- **Sidecar Architecture spec** (theme A) — see §6.1 below.
- **Storage Spec category** (theme B) — see §6.2.
- **Cross-repo extraction policy** (theme D) — must be ratified before brief 1.6 ships.
- **S3 storage spec implementation** (brief 1.6) — once policy decision made.
- **Operation-mode taxonomy** (theme E) — Architect review.

---

## 5. Brief updates needed

### 5.1 Amend `v0.1.140__sg-compute__migration/01__architecture.md`

Append a "Living updates 2026-05-04" section covering:

- §1 Taxonomy — every Node runs a sidecar; sidecar carries the documented auth contract; sidecar is part of the Node abstraction.
- §3 Platforms / §4 Spec contract — add the `OBJECT_STORAGE` capability example; reference the storage-spec pattern (Memory-FS seam).
- §6 Legacy mapping — mark closed migrations with their commit hash + closing dates.

Do **not** rewrite the body. The strategic baseline is still correct.

### 5.2 Amend `v0.1.140__sg-compute__migration/30__migration-phases.md`

Append a "Status as of 2026-05-04" column. Mark:

- B1 ✅, B2 ✅, B3.0-B3.7 ✅ (with note: linux dropped; needs B3.1 redo), B4 ⚠ façade, B5 ⚠ partial, B6 ⚠ dual-write, B7.A ⚠ dual-write, B7.B ⚠ dual-write, B8 ✅.
- F1 ✅, F4 ⚠, F7 ✅, F8 ✅, F9/F10 deferred-as-planned.
- Add a new B3.x slot for `s3_server` spec (out-of-band addition; not a migration).

### 5.3 Amend `v0.1.140__sg-compute__migration/10__backend-plan.md`

Add a closing-status section per phase. Add the gap-closure phase as **B3.1-redo** + **B4-completion** + **B5-completion** + **B7-cleanup** as enumerated items in the new gap-closure brief (§6.3 below).

### 5.4 Re-scope `v0.1.140__post-fractal-ui__backend/04__vault-write-contract.md`

Firefox is no longer the obvious first consumer. Sidecar (boot artefacts? call-log archives?) and S3 server (call-log persistence per theme B) are now competing first-consumers. Architect to re-scope before any consumer ships.

### 5.5 Update `v0.1.140__post-fractal-ui__backend/01__plugin-manifest-endpoint.md`

The brief's `Schema__Plugin__Manifest` was renamed in code to `Schema__Spec__Manifest__Entry`. Either close the brief as DELIVERED with renamed terms, or amend and keep open.

### 5.6 Archive `v0.1.140__host-control-plane/` and `v0.1.140__host-control-plane-ui/`

Both are functionally superseded by `sg_compute/host_plane/` (commit c3fc219) and the actual sidecar UI on `dev`. Move to `team/comms/briefs/archive/v0.1.140__host-control-plane__c3fc219/` with a banner.

---

## 6. New briefs to commission (priority order)

### P-1 (urgent — blocks all further forward motion)

**6.1 Backend gap-closure brief** — `team/comms/briefs/v0.1.169__sg-compute-gap-closure__backend/`
The single most important new commission. Closes G1-G5 (linux spec, B4 control-plane wire-up, per-spec CLI dispatcher, B5 validate, B6/B7.A/B7.B shim discipline, capability enum lock). Owner: Backend Sonnet. Two-PR brief (smaller PR for linux+capability-lock; larger PR for B4+B5+B7 cleanup).

**6.2 Sidecar Architecture spec** — `team/comms/briefs/v0.1.169__sidecar-architecture/`
Documents the now-first-class sidecar contract: auth modes, CORS layer, port (lock to one), `/docs-auth`, boot log + pod log + pod stats endpoints, WS shell with cookie auth, allowlist. Owner: Architect.

**6.3 Cross-repo extraction policy** — `team/comms/briefs/v0.1.169__spec-repo-extraction-policy/`
Decides: is S3 a one-off exception that gets its own repo before phase 8, or is every new spec extracted to its own repo from day one, or does S3 wait until phase 8 like everything else? Blocks brief 1.6. Owner: Architect (decision-only).

### P-2 (important; follow-up within 2 weeks)

**6.4 Storage Spec category** — `team/comms/briefs/v0.1.169__storage-spec-category/`
Defines what makes a "storage spec", what the common Memory-FS-backed interface is, how Stacks compose workload+storage. First consumer is `s3_server`; future consumers include vault-blob and local-fs. Owner: Architect + Storage-S3 lead.

**6.5 Sidecar↔SP-CLI catalog ownership boundary** — `team/comms/briefs/v0.1.169__sidecar-vs-control-plane-boundary/`
Commit `1c96fbe` ("ec2-info: move to SP CLI catalog (has IAM) — remove from sidecar (no IAM)") reveals an in-flight design that should be a written contract: which routes belong on the sidecar vs the management plane? Owner: Architect.

**6.6 Frontend gap-closure brief** — `team/comms/briefs/v0.1.169__sg-compute-gap-closure__frontend/`
Once 6.1 lands (B4 fixed), frontend has F2/F3/F5/F6 plus the F4 per-type-namespace finish to ship. Plus the post-fractal-UI decision-only items. Owner: Frontend Sonnet.

### P-3 (lower urgency; commission when capacity allows)

**6.7 Operation-mode taxonomy** — `team/comms/briefs/v0.1.169__spec-operation-modes/`
Validate the FULL_LOCAL/FULL_PROXY/HYBRID/SELECTIVE pattern from brief 1.6 against ≥2 specs before generalising into the SDK contract. Owner: Architect.

**6.8 Call-log persistence contract** — `team/comms/briefs/v0.1.169__call-log-persistence/`
Brief 1.9 mandates a discovery-first call log. Where do those logs live (in-process, Memory-FS, CloudWatch, S3-recursive, vault)? If vault, this touches BE-04 (vault-write contract). Owner: Architect + Dev.

**6.9 Host-plane port stabilisation sweep** — Librarian convention sweep (not a brief)
Original brief said `:9000`; sidecar briefs use `:19009`. Pick one, document it, sweep references in user-data scripts, reality docs, UI defaults. Owner: Librarian.

---

## 7. Recommended next actions

### For the backend team (next session)

> Read `team/humans/dinis_cruz/claude-code-web/05/04/22/00__executive-audit__sg-compute-migration.md`. Your next session is **gap-closure** — the brief at `team/comms/briefs/v0.1.169__sg-compute-gap-closure__backend/` (which I will write next). Top priorities, in order:
>
> 1. Migrate `linux` as a spec (B3.1 redo); add `extends=['linux']` to every dependent spec's manifest.
> 2. Wire `Routes__Compute__Nodes` end-to-end (POST/GET/DELETE) to `Node__Manager`.
> 3. Build `Routes__Compute__Pods` and `Pod__Manager`.
> 4. Add `sg_compute/control_plane/lambda_handler.py`.
> 5. Add per-spec `cli/` directories (all 8 specs) and wire the `sg-compute spec <id> <verb>` dispatcher.
> 6. Convert legacy paths (`__host/`, `agent_mitmproxy/`, all 8 `__cli/<spec>/`) to re-export shims with deprecation warnings.

### For the frontend team

> Hold on F2/F3/F5/F6 — they are backend-blocked on the gap-closure work. While you wait, you have unblocked work:
>
> 1. **F4 per-type namespace finish** — `sp-cli:plugin:*` → `sp-cli:spec:*` with deprecated aliases.
> 2. **Post-fractal-UI decision-only items** — FE-04.4 (firefox card label), FE-04.5 (plugin-folder structure decision), FE-05.4 (event-vocabulary spec).
> 3. **Storage viewer commit `0a15d0d`** — appears unbriefed; flag for retrospective ratification.

### For the Architect

> Three P-1 decisions due this week:
>
> 1. **Lock `Enum__Spec__Capability`**. The set in `sg_compute/primitives/enums/Enum__Spec__Capability.py` has been shipping unsanctioned for two days.
> 2. **Cross-repo extraction policy** — does S3 go to its own repo before phase 8, or wait? This blocks brief 1.6.
> 3. **Approve the gap-closure brief** before the backend team starts.

### For the Librarian

> Backlog additions (to `team/roles/librarian/DAILY_RUN.md`):
>
> - **B-014** — convention sweep: host-plane port `:9000` vs `:19009`. Pick one, document, sweep all references.
> - **B-015** — migrate the `sg-compute/` reality domain content from B3 commit-message bodies into the proper `team/roles/librarian/reality/sg-compute/index.md`.
> - **B-016** — archive `host-control-plane/` and `host-control-plane-ui/` briefs; redirect to `sg_compute/host_plane/` reality + sidecar architecture brief.

---

## Appendix — Top-line metrics

| Metric | Value |
|--------|-------|
| Commits since v0.1.140 | 165 |
| Backend phases delivered (full + partial) | 15 of 18 |
| Frontend phases delivered (full + partial) | 5 of 10 (4 of which were the F4 ⚠ + the small ones) |
| New briefs that emerged during execution | 6 brief folders + 3 human-only files |
| Strategic themes not in original plan | 5 |
| Trees in dual-write state | 5 (and counting if more specs migrate without shim discipline) |
| Top-priority new briefs to commission | 3 (P-1) |
| Estimated remaining critical-path effort | 1-2 sessions backend gap-closure + 2-3 sessions frontend + 3 P-1 decisions |
