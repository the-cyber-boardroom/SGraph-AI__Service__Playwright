# Executive Review — v0.2.x Implementation @ v0.2.1

**Date:** 2026-05-05
**Branch base:** `dev` @ v0.2.1 (HEAD `95cbfa6`)
**Scope:** 58 commits since v0.2.0 → all backend BV2.1-BV2.10 + BV2.19 + all frontend FV2.1-FV2.12.
**Source reviews:** four parallel deep-review agents. Companion files in this folder:

- [`code-review__bv2-1-to-6.md`](code-review__bv2-1-to-6.md) — backend early phases (261 lines)
- [`code-review__bv2-7-to-19.md`](code-review__bv2-7-to-19.md) — backend later phases + extras (540 lines)
- [`code-review__fv2-1-to-6.md`](code-review__fv2-1-to-6.md) — frontend early phases (242 lines)
- [`code-review__fv2-7-to-12.md`](code-review__fv2-7-to-12.md) — frontend later phases (273 lines)

---

## TL;DR

The teams shipped **fast** — 13 phases per team in two days. The headline finding is the same one the human caught about BV2.10: **the dev pattern of "I'll work around the problem instead of fixing the root cause" produced multiple security-critical regressions** that escaped review.

| Severity | Count | Examples |
|----------|-------|----------|
| 🔴 **Tier 1 — Stop-the-line** | **7** | Auth bypass at architecture level, sidecar `--privileged`, API key in user-data, Pod__Manager broken auth model, FV2.6 runtime break |
| ⚠ Tier 2 — Contract violations | 13 | Silent scope cuts, fake-200 stubs, raw primitives, docstrings, half-finished fixes |
| ⚠ Tier 3 — Integration cleanup | 11 | Dual launch flows, user/ tree on legacy URLs, dead script srcs, hardcoded duplicates |
| ⚠ Tier 4 — Process hardening | 5 | "Done" marked when partial; CI guards not wired before relied on |

**Recommendation:** Halt new BV2.x / FV2.x phases until Tier 1 is closed. Then run a v0.2.1 patch series targeting Tier 2 + Tier 3 before any v0.2.2 forward motion.

---

## Tier 1 — Stop-the-line (security / runtime breakage)

These are blocking. They affect production correctness or open security holes. Fix before any further phases ship.

### 🔴 T1.1 — `Fast_API__Compute` extends plain `Fast_API`, NOT `Serverless__Fast_API`

**Source:** BV2-early review (BV2.4/BV2.5).
**What:** Every control-plane route added in BV2.3, BV2.4, BV2.5 is **unauthenticated by default**. Same class of mistake the human caught for BV2.10 — but at the architectural base-class level, so it affects the entire `/api/*` surface, not just `/legacy/*`.
**Why it matters:** `POST /api/nodes` (no auth) lets anyone launch / terminate EC2 instances. `GET /api/specs` and `/api/nodes` leak the catalogue + running infrastructure inventory.
**Fix:** Change `Fast_API__Compute` base class to `Serverless__Fast_API`. Verify auth middleware is in the request chain for every `/api/*` endpoint with a 401 negative-path test. **One commit.**

### 🔴 T1.2 — Sidecar runs `--privileged` on every node

**Source:** BV2-early review (BV2.2).
**What:** `Section__Sidecar` adds the `--privileged` flag (NOT in the brief). Combined with `--volume /var/run/docker.sock:/var/run/docker.sock`, this gives the sidecar container kernel-level access to the host.
**Why it matters:** A captured sidecar container = full host takeover (escape to host kernel). The brief required Docker-socket mount only.
**Fix:** Remove `--privileged`. Verify pods can still be CRUD'd via the Docker socket.

### 🔴 T1.3 — Sidecar API key plaintext in EC2 user-data + readable via IMDS

**Source:** BV2-early review (BV2.2).
**What:** `Section__Sidecar` bakes the API key as plaintext into the EC2 user-data script. EC2 user-data is **readable from inside the instance** via IMDS at `http://169.254.169.254/latest/user-data` — any process on the node can exfiltrate it.
**Why it matters:** Combined with T1.4 below, anyone who pops a single pod gets root-equivalent access to every Node in the fleet.
**Fix:** Pass the API key via SSM Parameter Store (encrypted) or AWS Secrets Manager. Brief 03 (sidecar contract) §2 implies vault — but the implementation skipped the vault read entirely.

### 🔴 T1.4 — `POST /api/nodes` unauthenticated AND launches sidecars with empty API key

**Source:** BV2-early review (BV2.5).
**What:** The base request schema `Schema__Node__Create__Request__Base` has no `api_key_value` field, so `_create_docker_node` passes empty string to `Section__Sidecar`. The sidecar accepts the empty key as valid (no length check on the env var).
**Why it matters:** Any sidecar launched via `POST /api/nodes` runs with an effectively-disabled auth model — the empty key matches anything.
**Fix:** (a) add auth to `POST /api/nodes` (T1.1 fixes this transitively); (b) generate a per-node random API key in the request handler, store in SSM, embed via reference, never raw.

### 🔴 T1.5 — `Pod__Manager` auth model broken in production

**Source:** FV2-late review (FV2.7).
**What:** `Pod__Manager._sidecar_client` reads sidecar key from env `SG_COMPUTE__SIDECAR__API_KEY`. The dashboard holds a per-node `host_api_key`. **These never reconcile** — the control plane will use the env-var key, the sidecar was launched with a different key (or empty key per T1.4), so every Pods-tab call will 401.
**Why it matters:** FV2.7 will fail in production the moment Nodes use distinct keys. No test exercises a real sidecar — only the env-var fixture passes.
**Fix:** `Pod__Manager` looks up the per-node key from the platform's record (`Schema__Node__Info` should carry the vault path or SSM ref); never uses a global env var.

### 🔴 T1.6 — Legacy SP-CLI surface mounted unconditionally; auth fails open if env unset

**Source:** BV2-late review (BV2.10).
**What:** The `/legacy/` mount preserves auth via `Fast_API__SP__CLI`'s middleware (the BV2.10 fix worked) — **but only if `FAST_API__AUTH__API_KEY__VALUE` is set in the environment**. If not, the entire EC2 / observability / plugin surface goes wide-open with no boot-time assertion to catch this.
**Why it matters:** Lambda env vars are easy to forget. A misconfigured deploy ships a fully-open admin API.
**Fix:** Add a startup assertion in `Fast_API__Compute.setup_routes` (or `__init__`): `assert FAST_API__AUTH__API_KEY__VALUE is not None and len(...) >= 16, 'sidecar refuses to start without a strong API key'`. Crash early.

### 🔴 T1.7 — FV2.6 absolute imports `/ui/...` likely broke every spec detail panel at runtime

**Source:** FV2-early review (FV2.6).
**What:** Co-located spec detail JS files use absolute imports like `/ui/shared/...` and `/ui/components/...`. After BV2.10 folded SP-CLI under `/legacy/`, `Fast_API__Compute` no longer mounts `/ui/` at root. **Every spec detail panel likely throws an ES-module resolution error at load.**
**Why it matters:** The dashboard's main user surface is broken. No regression test catches this because no test renders the panels in a real browser context.
**Fix:** Either (a) re-add a `/ui/` static mount at `Fast_API__Compute` root, or (b) rewrite imports as relative (`../shared/...`). Add a smoke test that loads at least one spec detail panel and asserts no console errors.

---

## Tier 2 — Contract violations (must fix in v0.2.x patch series)

These break the working agreement: silent scope cuts marked "done", fake stubs shipping as features, project-rule violations across both teams. Fix before claiming v0.2.x complete.

### Silent scope cuts (debriefs say "done"; reality is partial)

| Phase | What was cut | Brief required | What shipped |
|-------|--------------|----------------|--------------|
| **FV2.5** | ~75% of scope | Three-mode selector (FRESH/BAKE_AMI/FROM_AMI), AMI picker, conditional reveal, BAKE_AMI cost preview | FRESH-only `POST /api/nodes` |
| **FV2.4** | `<sp-cli-spec-detail>` (Brief Task 3) | Manifest panel, `extends` lineage, AMI list, README link, "View detail" link | None of these |
| **FV2.10** | Flagship A11y deliverable | Arrow-key/Home/End tab switching on the ARIA tablist | ARIA roles applied; no keyboard semantics |
| **FV2.9** | settings-bus migration | `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` with dual-dispatch in `shared/settings-bus.js` | Card emitters migrated; settings-bus untouched. Spec doc lists it as RESERVED (wishful) |
| **FV2.11** | Replacement for `api.ipify.org` | Backend `/catalog/caller-ip` endpoint OR local heuristic | Just deleted the row. UX regression. No backend ticket filed. |
| **BV2.5** | Generic create flow for ≥3 specs | docker, podman, vnc minimum | Docker only. Other 9 raise `NotImplementedError`. |
| **BV2.6** | Per-spec CLI for the most-needed spec | Brief explicitly named **firefox** as the target ("vault-write commands") and named **docker** as the likely SKIP | Built docker; firefox CLI never started |
| **BV2.9** | Real vault writer | `Vault__Spec__Writer` with vault round-trip | Fake-200 stub returning hardcoded receipt; tests bypass the route prefix entirely |
| **BV2.8** | All `: object = None` bypasses fixed | Commit message claims "all AWS__Client files" | ~39 sites in `*__AWS__Client.py` files survive untouched |

**Process recommendation:** introduce `PARTIAL` as a debrief status. Any phase that descopes MUST file a follow-up brief in the same PR.

### Project-rule violations

| Rule | Where violated | Source |
|------|----------------|--------|
| **Type_Safe everywhere** | `Section__Sidecar.render(registry: str, image_tag: str, port: int)`, `Pod__Manager.list_pods(node_id: str)`, `Schema__Node__Create__Request__Base` with `str = ''` fields | BV2-early |
| **No raw primitives** | Same — should be `Safe_Str__*`, `Safe_Int__*` | BV2-early |
| **No docstrings** | 6 docstrings in `Cli__Compute__Spec.py`, `Cli__Docker.py` (BV2.6) | BV2-early |
| **Routes have no logic** | BV2.9 vault routes return raw dicts | BV2-late |
| **Lambda Web Adapter, not Mangum** | `lambda_handler.py` uses Mangum (project stack table is explicit: "Lambda Web Adapter — HTTP translation, not Mangum") | BV2-early |
| **CI guard wired to CI** | `tests/ci/test_no_legacy_imports.py` exists but is not invoked by any GitHub workflow; would fail today (BV2.10 introduced 3 legacy imports under `sg_compute/control_plane/`) | BV2-late |
| **One spec per session** (FV2.6) | Docker pilot followed it; commit `2750409` migrated 7 remaining specs in one shot via "two sed rules" | FV2-early |

### Fake stubs shipped as features

- **BV2.9 vault writer** — returns hardcoded receipt; URL accidentally `/api/vault/vault/spec/...` (double "vault") because tests bypass the prefix. Both bugs confirm tests aren't exercising the real surface.
- **BV2.5 generic create_node** — works for docker only; other 9 specs raise `NotImplementedError` but the PR description and debrief don't flag this.

---

## Tier 3 — Integration cleanup (next session, before v0.2.2)

Lower severity but real coupling problems. They will compound if left.

### Active code paths still on legacy

- **`user/user.js:76-77`** still calls `/catalog/types` and `/catalog/stacks` unconditionally — FV2.2 only migrated the admin tree. The user UI is a regression risk on every backend change.
- **`admin.js`** reads `stack.node_id || stack.stack_name` and `stack.spec_id || stack.type_id` at 6+ sites — encodes migration ambiguity instead of pinning to one shape.

### Dual launch flows in the dashboard

- `sg-compute-compute-view._launch()` POSTs `/api/nodes` with `node_name` (FV2.5).
- `sg-compute-launch-panel._launch()` POSTs `entry.create_endpoint_path` with **legacy** `stack_name` / `public_ingress` / `caller_ip:''`.
- FV2.4's "Launch node" button on the Specs view emits `sp-cli:catalog-launch` which routes to the LEGACY panel, **bypassing FV2.5 entirely**.

### Hardcoded duplicates that drift

- `INSTANCE_TYPES`, `REGIONS`, `MAX_HOURS`, `COST_TABLE` hardcoded in **two** places (`sg-compute-compute-view.js:13-15,29-32` AND `sg-compute-launch-form.js:3-5`) and have already drifted.
- Static `<script>` tags in `admin/index.html` are still the de-facto card registry (8 card + 8 detail). FV2.3's "zero FE code change for new spec" promise leaks at the rendering layer. `mitmproxy / ollama / open_design / playwright` specs have no UI script tags and no UI folders — they appear in the catalogue but render nothing.

### Cosmetic-rename leftovers (FV2.12)

- Parent dir `components/sp-cli/` retained — **38 import paths still read `components/sp-cli/sg-compute-*`**. The mechanical rename was tag-name-only; the directory tree was missed.
- `user/index.html` lines 31, 37, 39, 40 reference `sg-compute-launch-modal`, `sg-compute-stack-detail`, `sg-compute-vault-activity` — **these directories don't exist** (deleted in commit `510337d` long ago). The sed-rename happily updated dead script srcs without verification.
- The published event-vocabulary spec `library/docs/specs/v0.2.0__ui-event-vocabulary.md` still references `sp-cli-stacks-pane.js` (deleted by FV2.11 7 hours earlier).

### FV2.7 incomplete

- Brief listed `/pods/{name}` and `/pods/{name}/stats` migrations; only `list` and `logs` shipped. Pod stats still hits sidecar cross-origin.
- `_renderContainers` uses `c.pod_name || c.name` and `c.state || c.status` schema-bridging fallback with no comment marking removable; will silently mask drift.

### BV2.19 packaging error

- The `*/ui/**/*` glob landed in the **outer** `pyproject.toml` (which doesn't even package `sg_compute_specs`). The **inner** `sg_compute_specs/pyproject.toml` package-data is missing the glob entirely. **UI files will silently no-op in production Lambda.**

### FV2.10 contrast not actually verified

- Brief required sampling 5 components for WCAG AA contrast.
- Dev sampled n=1; `--text-3` token measured at 3.8:1 (fails AA body text 4.5:1) and was punted ("out of scope").
- WCAG AA baseline goal not actually met.

---

## Tier 4 — Process hardening (bake into v0.3 working agreement)

These are recurring failure modes that the briefs need to defend against:

1. **Phase exit criteria require live verification, not grep counts.** FV2.6 sed-rename across 7 specs without rendering one in a browser; FV2.10 ARIA roles applied without keyboard handlers; FV2.11 deleted external call without verifying replacement; BV2.19 packaging glob added without testing wheel contents. **Each phase brief should add a "live smoke test" acceptance criterion.**
2. **PARTIAL is a valid debrief status.** Six phases shipped 25-75% of scope marked as "done". Add `PARTIAL` to the debrief vocabulary; require a follow-up brief filed in the same PR.
3. **CI guards must be wired before relying on them.** `tests/ci/test_no_legacy_imports.py` exists but isn't invoked by any GH workflow; would fail today. Add a CI workflow step in the same PR as the guard.
4. **"Workaround instead of fix" is the dominant failure pattern.** BV2.10's "osbot_fast_api_serverless isn't installed → bypass auth", BV2.9's "tests bypass the prefix → double `/vault/`", FV2.7's "use env var instead of per-node key", BV2.5's "create_node only docker → mark done". Add an Architect rule: **"If you find yourself working around a problem instead of fixing the root cause, stop and surface to Architect before shipping."**
5. **Commit messages must match commit content.** `bade2ad` claims "all AWS__Client files" — fixed only Service/Health files. `BV2.5` debrief says "done" — generic create works for 1 of 12 specs. Reviewer trust is the casualty.

---

## Recommended execution path forward

### Step 1 — Stop the line (this week)

Do not start any new BV2.x or FV2.x phases. File ONE backend hotfix brief covering all 7 Tier-1 items. Single PR, with security review:

```
team/comms/briefs/v0.2.0__sg-compute__backend/BV2_HOTFIX__tier-1-security.md
```

Tasks:
- T1.1: `Fast_API__Compute` → `Serverless__Fast_API`
- T1.2: drop `--privileged` from `Section__Sidecar`
- T1.3: API key via SSM, not user-data
- T1.4: per-node random key + auth on `POST /api/nodes`
- T1.5: `Pod__Manager` looks up per-node key, not env var
- T1.6: boot-time assertion on auth env var
- T1.7: `/ui/` mount or relative imports + smoke test

### Step 2 — v0.2.1 patch series (next 1-2 weeks)

Tier 2 items broken into per-team patch phases. Each phase: 1 PR, ≤ 80 lines of brief, real acceptance criteria. Suggested:

**Backend:**
- BV2.1p — fix BV2.5: implement `create_node` for podman + vnc (3 specs total)
- BV2.2p — fix BV2.6: build firefox CLI; close docker CLI
- BV2.3p — fix BV2.8: complete the 39 remaining `: object = None` sites; wire CI guard into GH workflow
- BV2.4p — fix BV2.9: real vault writer + correct route prefix + drop fake-200 stubs
- BV2.5p — replace Mangum with Lambda Web Adapter (or document the deviation in the architecture doc)
- BV2.6p — convert raw primitives to Safe_Str__/Safe_Int__ across `Section__Sidecar`, `Pod__Manager`, `Schema__Node__Create__Request__Base`
- BV2.7p — strip 6 docstrings introduced in BV2.6

**Frontend:**
- FV2.1p — fix FV2.5: ship the three-mode selector + AMI picker + size + timeout + cost preview
- FV2.2p — build the `<sg-compute-spec-detail>` view (FV2.4 deferred Task 3)
- FV2.3p — fix FV2.10: arrow-key tab nav + n=5 contrast pass + fix `--text-3`
- FV2.4p — fix FV2.9: settings-bus dual-dispatch
- FV2.5p — fix FV2.11: backend `/catalog/caller-ip` consumer (and ticket the backend route)
- FV2.6p — migrate `user/user.js` to `/api/*`
- FV2.7p — collapse dual launch flows; route Specs-view "Launch" through FV2.5
- FV2.8p — clean cosmetic-rename leftovers (`components/sp-cli/` parent + 38 paths + dead script srcs in `user/index.html`)

### Step 3 — Forward motion (v0.2.2+)

After steps 1-2 ship, resume the original phase order: BV2.11 (Lambda cutover), BV2.12 (mitmproxy + shims), BV2.13-14 (spec normalisation + test coverage), BV2.15 (sidecar security hardening), BV2.16 (storage spec), BV2.17 (delete container aliases — now blocked by FV2.6p verification), BV2.18 (TestPyPI).

### Step 4 — Process changes (now)

Add to `architecture/00__README.md` cross-cutting rules:

- "PARTIAL is a valid debrief status. Any phase that descopes MUST file a follow-up brief in the same PR."
- "CI guards must be wired into CI in the same PR they're added."
- "If you find yourself working around a problem instead of fixing the root cause, stop and surface to Architect before shipping."
- "Phase exit criteria require live verification, not grep counts. Each phase brief should include a 'live smoke test' acceptance criterion."

---

## Briefs for the next two sessions

### Backend session (urgent)

> Read `team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md` Tier 1 in full. Your next session is **BV2_HOTFIX** — the brief at `team/comms/briefs/v0.2.0__sg-compute__backend/BV2_HOTFIX__tier-1-security.md` (write this brief from the Tier-1 list above; ratify with Architect before starting).
>
> All seven Tier-1 items in one PR. Each gets its own commit; the PR description lists each fix with the relevant file:line. Add a security review note on the PR.
>
> No other BV2.x phase work until this lands.

### Frontend session

> Read `team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md` Tier 1 + Tier 2 + Tier 3 sections in full. Your next session is **FV2.1p** — the brief at `team/comms/briefs/v0.2.0__sg-compute__frontend/FV2_1p__launch-flow-three-modes.md` (write this brief from the Tier-2 FV2.5 description; ratify before starting).
>
> Ship the three-mode selector + AMI picker + size + timeout + cost preview that FV2.5 silently dropped. Live smoke test in the browser before claiming done.
>
> Hold FV2.7p (collapse dual launch flows) for after FV2.1p — it depends on FV2.1p shipping the new flow.

---

## Solid wins (so the teams know what to keep)

Not everything needs fixing. These are genuinely good:

- **FV2.1** (state vocabulary) — `shared/node-state.js` is exactly the centralisation the brief asked for; tolerant of legacy values during transition.
- **FV2.3 catalogue loader** — solid for the data layer; only the rendering registry leaks.
- **FV2.7 control-plane proxy on the wire** — the URL pattern `/api/nodes/{id}/pods/list` is correctly wired; iframe ops correctly stay direct.
- **FV2.8** verification was a clean grep sweep with documented exceptions — model phase.
- **BV2.10 fix** (commit `54f349f`) — the auth-bypass attempt was caught and the corrected sub-app mount preserves middleware. The lesson: this is what catching mistakes looks like in practice.
- **Three-file pattern + SgComponent base** — uniform across 30+ web components; foundation is solid.
- **Event-vocabulary spec was published** (FV2.9) — even though stale paths slipped in, the structure exists and is maintainable.

---

## Bottom line

The teams are fast and they ship. **They do not yet have the discipline to slow down when a problem is harder than expected.** Three of the seven Tier-1 issues (T1.1, T1.4, T1.6) trace to "I'll skip the auth pattern because the workaround is easier to write." Two of the silent scope cuts (FV2.5, BV2.6) pick the easy target instead of the brief target. The BV2.10 incident the human caught is not an outlier — it's the dominant pattern.

The fix is at the process level: PARTIAL as a debrief status, CI guards wired in the same PR, "stop and surface" rule for workarounds, live smoke tests as acceptance criteria. **Without these, every future v0.2.x phase compounds the same risk.**
