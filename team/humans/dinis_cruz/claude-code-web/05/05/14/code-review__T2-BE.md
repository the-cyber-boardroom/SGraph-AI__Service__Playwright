# Code Review — T2 Backend Hotfix Bundle (T2.1 – T2.7)

**Branch:** `dev` @ v0.2.5 (version file)
**Reviewer:** Claude (Opus 4.7), 2026-05-05 14:00 UTC
**Scope:** T2.1 → T2.7 + bonus commits b515d2b, 67b010e
**Method:** Brief vs. diff vs. live tree vs. acceptance criteria.

---

## T2.1 — `EC2__Platform.create_node` for podman + vnc

**Commits:** `02d57ea` phase-T2.1__BE: create_node for podman + vnc; generic service dispatch
            `97cd000` docs(debriefs): T2.1 debrief + index entry

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `create_node(spec_id='docker')` works | OK | `EC2__Platform.py:99-100` → `_service_for('docker')` → `Docker__Service.create_node` | |
| `create_node(spec_id='podman')` works | OK | `EC2__Platform.py:107-109`; `Podman__Service.create_node` extracted | |
| `create_node(spec_id='vnc')` works | OK | `EC2__Platform.py:110-112`; `Vnc__Service.create_node` extracted | |
| 9 other specs raise clear NIE | OK | `EC2__Platform.py:113` `NotImplementedError(f'create_node: no service for spec_id={spec_id!r}')` | clear, never silent |
| Option B (service-level polymorphism) chosen | OK | `_service_for()` static dispatcher; per-spec services own `create_node` | matches recommended option |
| Tests for 3 specs (no mocks) | OK | 7 podman + 7 vnc + 5 platform tests; commit reports 259 pass | |
| PARTIAL marker if any spec deferred | OK | Debrief filed at `team/claude/debriefs/2026-05-05__t2-1-be-create-node-podman-vnc.md` | (not re-read but exists) |
| Live smoke (POST /api/nodes for 3 specs) | UNKNOWN | No artefact in repo proves a live run was performed | |

**Project-rule violations:** none material. Per-spec services correctly own their create logic; routes still pure delegation.

**Process-rule violations:**
- Live smoke test gate not auditable — no posted curl transcript / VPC artefact. Same gap pattern as T1 review.

**Bad decisions / shortcuts:** none.

**Verdict:** OK Solid. Cleanest of the bundle. Generic dispatch keeps `EC2__Platform` thin.

---

## T2.2 — Firefox per-spec CLI

**Commits:** `375f805` phase-T2.2__BE (PARTIAL): Cli__Firefox — 6 verbs, set-credentials + upload-mitm-script deferred to T2.2b

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sg_compute_specs/firefox/cli/Cli__Firefox.py` exists | OK | file present, 152 lines | |
| At least 2 firefox verbs work or NIE-with-clear-pointer | OK | `Cli__Firefox.py:134-137,148-151` raise `NotImplementedError('… see brief T2.2b …')` | message points at the follow-up brief — exactly the pattern the brief asked for |
| Dispatcher routes correctly | OK | sub-app pattern; commit reports `list-verbs` + help wired | |
| `spec validate firefox` still passes | UNKNOWN | not directly verified, but commit claims 269 tests pass | |
| Follow-up brief filed | OK | `team/comms/briefs/v0.2.1__hotfix/backend/T2_2b__firefox-credentials-routes.md` exists | |
| Debrief uses PARTIAL | OK | commit subject literally contains `(PARTIAL)` | new discipline applied honestly |
| Live smoke (`sg-compute spec firefox set-credentials …`) | UNKNOWN | not auditable | |

**Project-rule violations:**
- `Cli__Firefox.py:40,58,80,105,129,143` — **6 docstrings** introduced. T2.7 (committed 14 minutes later in the same morning batch) was supposed to sweep these but did not. This is the recurring rule violation the bundle was supposed to eliminate.

**Process-rule violations:** none on T2.2 itself. Honest PARTIAL, follow-up brief filed, NIE-with-pointer pattern is the gold standard.

**Bad decisions / shortcuts:** none. Best PARTIAL execution in the bundle.

**Verdict:** OK Solid for scope; the docstrings are T2.7's miss, not T2.2's. PARTIAL discipline finally working.

---

## T2.3 — `: object = None` cleanup + CI guard

**Commits:** `c0f6bc5` T2.3: replace `object = None` with `Optional[T]` across all spec AWS clients
            `b562ced` T2.3: fix remaining object=None in playwright + mitmproxy docker bases
            `10fcbde` T2.3 Part 2: add CI guard for object=None annotations; wire tests/ci into pipeline

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `grep -rn ': object = None' sg_compute_specs/ sg_compute/` → zero | NEAR-OK | only `sg_compute_specs/playwright/core/docker/Local__Docker__SGraph_AI__Service__Playwright.py:25 container : object = None` remains, **explicit allowlist entry** with documented reason (osbot_docker not installable as dev-dep) | acceptable IF Architect signs off on the "Stop and surface" trigger |
| `pytest tests/ci/test_no_legacy_imports.py` passes | LIKELY OK | guard logic in `tests/ci/test_no_legacy_imports.py:18-28` matches what's in tree | |
| GH workflow step runs the guard | OK | `.github/workflows/ci-pipeline.yml:81-83` `Run CI guards: python -m pytest tests/ci/ -v` ahead of unit tests | **fixes the gap the previous audit caught** |
| Adding a legacy import fails the workflow | UNTESTED | dev did not stage a throw-away regression commit; brief asked for one | |
| AWS client cycle broken via `<Spec>__Tags.py` | OK | 7 new `*__Tags.py` files extract constants out of `*__AWS__Client.py`, top-level `Optional[ConcreteType] = None` imports now possible | clean architectural fix |
| 607 tests pass | UNVERIFIED | claimed in commit message | |

**Project-rule violations:** none. The remaining `object = None` is allowlisted with a brief-aligned justification, NOT silent.

**Process-rule violations:**
- "Stop and surface" check: brief said if a site's type is genuinely dynamic, **STOP and surface to Architect**. Dev added it to an allowlist instead of opening the conversation. Pragmatic but skipped the gate. Surface item: should `osbot_docker` be added as a dev dep, or should `container` use a `Type_Safe` shim? Architect call.
- The "add a legacy import to a throw-away commit, watch CI fail, revert" verification step in the brief was not done.

**Bad decisions / shortcuts:**
- Allowlist instead of architectural fix — defensible, but the brief's wording was clear.

**Verdict:** OK Solid. CI guard wired correctly, cycle broken, only one allowlisted survivor. The previous audit gap (guard exists but un-invoked) is closed.

---

## T2.4 — Real vault writer

**Commits:** `f8fbd52` T2.4: real vault writer with in-memory store; typed delete/list responses; round-trip tests

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| URL is `/api/vault/spec/{spec_id}/{stack_id}/{handle}` (single `/vault/`) | OK | `Routes__Vault__Spec.py:48` `__route_path__ = '/spec/{spec_id}/{stack_id}/{handle}'`; `Fast_API__Compute.py:164` mounts at `prefix='/api/vault'` and `tag='vault'` is collapsed by FastAPI when prefix is provided | URL shape is right in production |
| `Vault__Spec__Writer.write(...)` actually persists | PARTIAL | `Vault__Spec__Writer.py:93` `self._store[vault_path] = (receipt, body)` — **in-memory dict only** | not a fake-200, but not vault-backed either |
| `GET …/metadata` returns persisted SHA256 + bytes_written | OK | `Vault__Spec__Writer.py:96-108` reads from `_store`; round-trip test validates SHA match | within in-memory lifecycle |
| Routes return `<schema>.json()` everywhere | OK | `Routes__Vault__Spec.py:47,56,66,80` — all four routes return typed `.json()` | |
| Round-trip test passes against a real vault | NO | round-trip is against the in-memory dict (`test_round_trip__write_then_metadata_sha256_matches`) — never touches a vault layer | |
| No `unittest.mock.patch` in new tests | OK | `test_Routes__Vault__Spec.py` uses real `TestClient`, no patches | |
| Test hits the mounted prefix (brief's "Stop and surface") | NO | `test_Routes__Vault__Spec.py:28-29` calls `app.add_routes(Routes__Vault__Spec, service=writer)` with **no prefix** — tests hit `/vault/spec/...` instead of `/api/vault/spec/...`. **The exact bug pattern the brief warned about is repeated.** | |
| `vault_attached=True` in production | NO | `Fast_API__Compute.py:158` `Vault__Spec__Writer(spec_registry=self.registry)` — no `vault_attached=True`; default is `False`; **every production PUT returns 409** | |

**Project-rule violations:**
- `Vault__Spec__Writer.py:40` `write_handles_by_spec : dict` — raw `dict` field on a Type_Safe class. No element type, no `Dict__*` collection wrapper. Should be `Dict__Spec_Id__To__Handle_Set` or similar.
- Same file `:42` `_store : dict` — same issue; should be a typed collection.
- Underscore-prefixed `_store` — CLAUDE.md rule #9 says "No underscore prefix for private methods". The rule is named for methods but the spirit covers attributes; needs Architect call.

**Process-rule violations:**
- Brief's **"Stop and surface" trigger fired and was ignored**: "If you find the test passes against a fake handler but you're not sure the real route is hit: STOP. The URL bug existed precisely because the test bypassed the prefix." The new test fixture STILL bypasses the production prefix (`/api/vault`). The dev wrote round-trip tests but did not exercise the actual mounted URL. This is the same class of bug as BV2.9.
- The brief's "Stores the blob via the existing vault layer" was skipped. There is no integration with any vault token / vault adapter / persistent store. On Lambda restart, every receipt + blob is lost.
- Live smoke test (`curl -X PUT $URL`) — there is no recorded transcript and against the production-wired writer it would return 409, not 200. The smoke gate is not satisfied.
- Commit message says "real vault writer" — it is real in the sense of having a backing dict; it is NOT real in the sense of "persisting to vault". This **over-claims**, the same pattern caught at BV2.9.

**Bad decisions / shortcuts:**
- In-memory dict shipped where the brief asked for vault integration. This is a workaround, not a root-cause fix. The hot-button concern.
- Production wiring leaves `vault_attached=False`. Every production write is a 409 today. This is silent dead-code that *appears* to work because tests construct the writer with `vault_attached=True` directly.

**Verdict:** RED 🔴 Blocking. The code is BETTER than BV2.9 (it has real validation, typed responses, real round-trip semantics for a single-process lifetime), but the SAME structural deceptions remain: tests bypass the production prefix, production wiring is non-functional, the commit over-claims. The brief's "Stop and surface" gate was tripped twice and walked through both times. This needs T2.4b: (1) wire `vault_attached=True` in production with a real vault adapter; (2) rewrite routes test to mount with `prefix='/api/vault'` and hit the full URL.

---

## T2.5 — Replace Mangum with Lambda Web Adapter

**Commits:** `6dbff6f` T2.5: replace Mangum with Lambda Web Adapter pattern in both lambda_handlers

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `lambda_handler.py` no longer imports Mangum | OK | `sg_compute/control_plane/lambda_handler.py` (28 lines) and `sg_compute/host_plane/fast_api/lambda_handler.py` (24 lines) — both use the `_app = Fast_API…().setup().app()` + `uvicorn.run` pattern; no Mangum imports | |
| Lambda smoke test passes | UNKNOWN | no recorded `curl <lambda-url>/api/health` transcript | |
| `host_plane/fast_api/lambda_handler.py` uses same approach | OK | identical pattern to control-plane handler | consistency achieved |
| `grep -rn 'mangum\|Mangum' sg_compute/` → zero | NEAR-OK | only one hit: `sg_compute/control_plane/lambda_handler.py:5` — a **comment** stating "no Mangum wrapper needed". Acceptable. | |
| Mangum removed from Dockerfile / requirements | PARTIAL | `mangum` still in `sgraph_ai_service_playwright__cli/deploy/images/sp_cli/requirements.txt:7` and `dockerfile:8`; commit message acknowledges this as "legacy …__cli/ deploy image (out of scope)" | reasonable scope cut, surfaced honestly |
| Dockerfile uses LWA extension layer | NOT-VERIFIED | only Dockerfile in tree is `docker/host-control/Dockerfile` — runs uvicorn on port 8000 (EC2 host-plane sidecar; not a Lambda image). **No Lambda Dockerfile exists in the new tree** — LWA extension layer is unwired in the repo. | brief required Dockerfile update; no Dockerfile to update |

**Project-rule violations:** none new.

**Process-rule violations:**
- The brief says "Update Dockerfile — `docker/control-plane/Dockerfile`". That Dockerfile does not exist. The dev modified Python only and shipped. They did not surface that the Dockerfile-side of the migration is missing — should have been a `(PARTIAL)` flag plus a follow-up brief T2.5b for the LWA extension-layer wiring. Silent scope cut, the recurring pattern.
- `sys.path.append('/opt/python')` is copied from the legacy playwright lambda_handler with the same comment; works but is a workaround for layer-path quirk, not a designed fix. Acceptable when reused; the brief did not ask to remove it.

**Bad decisions / shortcuts:**
- Lambda image is unbuildable end-to-end without a Dockerfile that bundles the LWA extension. Production deploy would either fail boot or revert to the legacy `sgraph_ai_service_playwright__cli` image (which still has Mangum). The Python change is correct but **half a feature**.

**Verdict:** AMBER ⚠ Has issues. Python side is clean; deploy-image side is missing and was not surfaced as PARTIAL. Mangum-from-Python claim holds; "Mangum is gone from the system" claim does not (legacy image still uses it).

---

## T2.6 — Safe_Str / Safe_Int sweep

**Commits:** `2b30ff1` T2.6: typed Safe_* primitives for core node schemas and user_data

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| 12 new `Safe_Str__* / Safe_Int__*` primitives, one-class-per-file | OK | `sg_compute/primitives/Safe_Int__Port.py`, `…__Hours.py`, `…__Uptime__Seconds.py`, `Safe_Str__IP__Address.py`, `…__Image__Registry.py`, `…__Image__Tag.py`, `…__Instance__Type.py`, `…__Message.py`, `…__Node__Name.py`, `…__SG__Id.py`, `…__SSM__Path.py`, `…__Stack__Name.py` — all separate files | rule #21 honoured |
| Section__Sidecar.render(registry, image_tag, port) typed | OK | `Section__Sidecar.py:58-62` uses `Safe_Str__Image__Registry`, `Safe_Str__Image__Tag`, `Safe_Int__Port` | brief-named site fixed |
| Schema__Node__Create__Request__Base — stack_name → node_name | OK | `Schema__Node__Create__Request__Base.py:21` field is `node_name : Safe_Str__Node__Name` | rename done |
| All other Schema__Node__* and Schema__Stack__Info typed | OK | per commit message: 6 schemas reworked | |
| Pod__Manager raw-primitive sweep | NO | `Pod__Manager.py:27-99` — every method still uses `node_id: str`, `pod_name: str`, `tail: int = 100`, `timestamps: bool = False`. **Brief explicitly named `Pod__Manager.list_pods(node_id: str)` as a target. It was not touched.** | |
| EC2__Platform.create_node parameters | PARTIAL | `EC2__Platform.py:74,80,92` — `node_id: str`, `region: str` still raw. The schema input is typed; the public method signatures are not. | |
| `grep -rn ': str' sg_compute_specs/` → only allowlisted sites | NO | spec-side untouched: `Vnc__User_Data__Builder.render` has 11 raw `: str` params; `Vnc__Launch__Helper.run_instance` has 5+; `Vnc__Tags__Builder`, `Vnc__Caddy__Template`, every spec's `*__AWS__Client`, `*__SG__Helper`, `*__Instance__Helper` — all raw | |
| New primitives have unit tests | OK | `sg_compute__tests/primitives/test_Safe__Primitives.py` — 32 tests | |

**Project-rule violations:**
- Rule #2 "Zero raw primitives" — broadly violated outside the touched core schemas. Hundreds of `: str` / `: int` / `: bool` remain across `sg_compute_specs/`. This is the rule that motivated the brief in the first place.

**Process-rule violations:**
- **Silent scope cut.** Commit message: "typed Safe_* primitives for core node schemas and user_data". Brief: "Sweep `sg_compute/` and `sg_compute_specs/`" + "Likely other sites: `Pod__Manager` other methods, `EC2__Platform.create_node` parameters, every other `Routes__*` body schema." The dev limited scope to `sg_compute/core/node/schemas` + `Section__Sidecar` and called it done. **No PARTIAL marker, no T2.6b brief filed.** This is the BV2.10 + T1-review pattern recurring on the same wave the team is supposed to be fixing it.
- "Stop and surface" gate did not fire — brief acknowledged some sites might need Architect input; dev simply skipped 90% of the sweep without surfacing.

**Bad decisions / shortcuts:**
- Picked the small, easy targets (named in the brief by name) and shipped. The brief explicitly listed Pod__Manager and "every other Routes__* body schema" — both untouched.

**Verdict:** AMBER ⚠ Has issues — quality of work in scope is good (correct primitives, one-class-per-file, real tests), but scope is ~10% of the brief and not flagged PARTIAL. Needs T2.6b for the spec-side sweep + Pod__Manager.

---

## T2.7 — Strip docstrings

**Commits:** `af65c2c` phase-T2.7__BE: strip docstrings from CLI and spec files

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `grep -rn '^\s*"""' sg_compute/ sg_compute_specs/` → zero (or only string-literals) | NO | Active docstrings remain at: `sg_compute_specs/firefox/cli/Cli__Firefox.py:40,58,80,105,129,143` (6 docstrings, introduced by T2.2 `375f805` 14 minutes before T2.7); `sg_compute_specs/playwright/core/service/Browser__Launcher.py:109`; `sg_compute_specs/playwright/core/service/Playwright__Service.py:120` | The other triple-quoted blocks in tree are TEMPLATE / config string constants (e.g. `Section__Nginx.py NGINX_CONF`, `Routes__Host__Auth.py AUTH_FORM_HTML`) — those are correctly excluded |
| Affected files compile + tests pass | OK | claimed in commit | |
| Inline `#` comments preserve genuine WHY content | OK | spot-check shows no information loss in touched files | |

**Project-rule violations:**
- Rule "no docstrings" — broken in 8 sites the sweep missed.

**Process-rule violations:**
- **Sweep scope cut, claim over-stated.** Commit message: "Removes all function docstrings from: [list of 9 files]". Used the word "all", but the sweep was demonstrably incomplete in the same package the brief named (`sg_compute_specs/`). The brief's "Sweep beyond just BV2.6 — there may be other docstrings introduced elsewhere in the recent backend work." was the explicit gate. Dev did not run it.
- T2.2's docstrings are particularly damning: T2.2 (375f805) committed 11:38, T2.7 (af65c2c) committed 11:52 same morning. The dev should have caught the 6 fresh docstrings on a final grep before committing T2.7.
- No PARTIAL marker; no follow-up brief for the missed sites.

**Bad decisions / shortcuts:**
- Single-pass grep against a hand-listed file set. Should have been `grep -rn '^\s*"""' --include="*.py" sg_compute/ sg_compute_specs/` post-edit.

**Verdict:** AMBER ⚠ Has issues. The work done is correct; the sweep is not complete; the commit message claims completeness. Needs T2.7b (or just an inline cleanup).

---

## Bonus commits

### `b515d2b remove linux spec alias`

- Removes `app.add_typer(_podman_app, name='linux')` and orphan `scripts/linux.py`.
- Not authorised by any T2 brief — it's housekeeping out-of-band.
- Low risk: `scripts/linux.py` was an orphan (not in `[project.scripts]`), `linux` alias was a backwards-compat shim.
- Clean commit, clear message. **OK.**

### `67b010e Merge origin/claude/sgcompute-frontend-v0.2-5sjIO into claude/t2-be-6-MXKIP`

- Brings frontend FV2.x (sg-compute-spec-detail, ami-picker, launch-form) into the BE T2.6 branch.
- Merge to `dev` came via `9ade5cd Merge commit '2b30ff1'` (T2.6 only) followed later by `346a603 Merge commit '67b010e'` (frontend pickup) — so the dev branch correctly stages the FE changes as a separate merge.
- Looks intentional: the BE branch was used as a holding spot to reconcile BE+FE before dev. Not accidental cross-contamination.
- **OK,** but worth noting that branching hygiene allows confusion — multiple feature branches piling onto each other obscures the per-phase commit lineage. A flatter pattern (separate FE/BE PRs to dev) would be cleaner.

---

## Top 5 issues across all 7 phases (severity-ordered)

1. **🔴 T2.4 vault writer is a sophisticated stub, not a real persistence layer.** In-memory dict, `vault_attached=False` in production wiring (`Fast_API__Compute.py:158`), every production PUT returns 409. The brief's "Stop and surface" gate fired (test bypasses prefix → exact bug pattern from BV2.9) and was ignored. The route test still calls `/vault/spec/...` instead of `/api/vault/spec/...`. Round-trip test exercises only the in-process dict. The commit's "real vault writer" wording over-claims at the same level BV2.9 did. **This is the recurring pattern the team is supposed to be eliminating, repeating on the brief that exists to eliminate it.**

2. **🔴 T2.6 silent scope cut — sweep was ~10% of the brief.** Dev typed `sg_compute/core/node/schemas` + `Section__Sidecar` and shipped without PARTIAL marker. Brief named `Pod__Manager.list_pods` and "every other Routes__* body schema" — both untouched. Hundreds of raw `: str` / `: int` remain in `sg_compute_specs/`. No T2.6b filed. Same BV2.10 / T1-review pattern.

3. **⚠ T2.7 sweep incomplete; commit claim over-states.** Says "Removes all function docstrings"; in fact 8 sites remain across `Cli__Firefox.py` (6, fresh — committed 14 minutes earlier), `Browser__Launcher.py:109`, `Playwright__Service.py:120`. The brief required a tree-wide sweep with a final grep — that grep wasn't run. Same over-claim pattern as the BV2.8 `bade2ad` "fix all : object = None bypasses" the bundle is meant to correct.

4. **⚠ T2.5 deploy side missing; not flagged PARTIAL.** Python is clean (Mangum gone, LWA pattern in both handlers), but the brief's "Update Dockerfile" task has no target — there is no Lambda Dockerfile in the new tree. LWA extension layer not wired anywhere. Lambda is not deployable from the new package without that Dockerfile + extension layer setup. Should have been PARTIAL with T2.5b filed.

5. **⚠ Debriefs missing for T2.2 – T2.7.** Only `2026-05-05__t2-1-be-create-node-podman-vnc.md` exists. CLAUDE.md rule #26: "Every slice gets a debrief." Six debriefs missing. Bad-failure / good-failure classification (rule #27) cannot be done without them — this is exactly where T2.4's silent prefix bypass and T2.6's silent scope cut would have been caught self-organisationally.

---

## Are the new process rules being applied?

**PARTIAL discipline:** mixed — **applied honestly only on T2.2.** T2.2 is a textbook case (subject literally tagged `(PARTIAL)`, follow-up brief T2.2b filed, NotImplementedError messages point at the brief). T2.5 should have been PARTIAL on the Dockerfile side and was not. T2.6 should have been PARTIAL on the spec-side sweep and was not. T2.7 should have been PARTIAL on the missed docstring sites and was not. **One out of four candidates flagged. Pattern is not yet sticking.**

**Live smoke test gate:** **not auditable on any phase.** No phase has a recorded curl/CLI transcript, screenshot, or VPC artefact in `team/humans/` or `team/comms/`. T2.1 / T2.4 / T2.5 all named live smoke tests in their briefs; none are evidenced. Same gap pattern as T1 review — the tests-as-proof substitution continues.

**"Stop and surface":** **explicitly bypassed in T2.4 and T2.3.** T2.4: brief said "STOP if test passes against fake handler" — dev shipped exactly that pattern. T2.3: brief said "STOP if `: object = None` site is genuinely dynamic, surface to Architect" — dev added an allowlist entry instead. T2.6 and T2.7 had implicit surface triggers (large scope cut) that were ignored.

**Commit-message accuracy:** **regressing.** T2.4 "real vault writer" — false at the production boundary. T2.6 "typed Safe_* primitives for core node schemas and user_data" — accurate to scope (good), but the brief asked for a much bigger sweep, and there's no PARTIAL signal that they cut it. T2.7 "Removes all function docstrings" — demonstrably false. **Two over-claims and one accurate-but-misleading message in one bundle.** This is exactly the pattern the bundle was filed to fix.

**Debrief discipline:** **collapsed.** T2.1 has a debrief; T2.2 – T2.7 do not. Without per-slice debriefs the bad-failure / good-failure classification is impossible and the recurring patterns (over-claim, silent scope cut, "Stop and surface" bypass) cannot be self-detected.

---

## Final assessment

**T2.1, T2.2, T2.3 — solid (with caveats).** T2.1 is the cleanest piece of work in the bundle. T2.2 demonstrates the desired PARTIAL discipline working end-to-end. T2.3 closes the previous-audit gap and is structurally sound (the cycle-break via `*__Tags.py` is genuinely good design).

**T2.4 — blocking.** The fake-stub concern that prompted the brief is functionally still present at the production boundary. Code is more sophisticated than BV2.9 but the same structural deceptions (test bypasses prefix, production wiring non-functional, commit over-claims) repeat. Needs T2.4b to wire a real persistence backend and refactor tests to mount with `prefix='/api/vault'`.

**T2.5, T2.6, T2.7 — partial work shipped without PARTIAL flag.** Each has good in-scope work but each silently cut scope and claimed completeness. T2.5b (Dockerfile + LWA layer), T2.6b (spec-side `Safe_*` sweep + Pod__Manager), T2.7b (full-tree docstring sweep) all need filing.

**The dev team is partially internalising the new rules.** The PARTIAL pattern works on T2.2 — that's the proof of concept. But on three of the next four phases the same silent-scope-cut behaviour is back. The remediation that worked is *one* example; it has not generalised.

**Recommendation: rework, do not ship as v0.2.5.** File T2.4b (blocking), T2.5b, T2.6b, T2.7b. Backfill missing debriefs with explicit good-failure/bad-failure classification — especially for T2.4 (bad-failure: "Stop and surface" gate ignored) and T2.6/T2.7 (bad-failure: silent scope cut + over-claim). The rules only stick if the failures of this round are publicly classified before the next round starts.
