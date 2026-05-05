# Executive Review — T2 Hotfix Implementation @ v0.2.1

**Date:** 2026-05-05 14:xx UTC
**Branch base:** `dev` @ v0.2.1
**Scope:** 11 T2 commits since the T1 bundle landed.
**Companion files in this folder:**

- [`code-review__T2-BE.md`](code-review__T2-BE.md) — backend T2.1-T2.7 (one agent)
- [`code-review__T2-FE.md`](code-review__T2-FE.md) — frontend T2.1 + T2.2 (one agent)

---

## TL;DR

**The new process rules worked when applied. They were NOT applied uniformly.** That is the headline. Same team, same session window, same rules — three phases used them textbook-clean, four bypassed them silently.

**Backend verdict: REWORK.** T2.4 is **blocking** — the vault writer is a "fake-stub 2.0" with `vault_attached=False` in production wiring; **the dev repeated the exact prefix-bypass test bug the brief warned against, in the same brief**. T2.6 swept ~10% of scope without a PARTIAL flag. T2.7 missed 8 docstrings — including 6 added by T2.2 fourteen minutes earlier in the same session.

**Frontend verdict: PATCH.** T2.1 was textbook PARTIAL discipline (4 of 5 brief items shipped, AMI picker placeholder + new follow-up brief filed) but hides 2 real bugs. T2.2 was over-claimed COMPLETE despite four genuine gaps. Hardcoded duplicates **worsened 2 → 3 copies**.

| Severity | Count | Examples |
|---|---|---|
| 🔴 Blocking (T2.4 ship breaks vault in prod) | 1 | T2.4 fake-stub 2.0 + repeated prefix-bypass test bug |
| ⚠ Silent scope cut (PARTIAL not flagged) | 3 | T2.6 (10% of scope), T2.7 ("all" claim wrong), T2-FE-2 (over-claimed COMPLETE) |
| ⚠ Hidden bugs under "PARTIAL" cover | 2 | T2-FE-1 `ami_name` data-loss, `creation_mode` kebab vs underscore |
| ⚠ Process-rule bypasses | 3 | 6 of 7 BE phases have no debrief; "Stop and surface" explicitly bypassed in T2.4 + T2.3; live smoke tests not auditable |
| ✅ Solid wins | 5 | T2.1 BE solid, T2.2 BE PARTIAL textbook, T2.3 CI guard finally wired, T2.1 FE PARTIAL textbook + follow-up brief filed, T2.2 FE structurally complete |

---

## The most important finding — "fake-stub 2.0"

**T2.4 is the showcase failure.** The brief explicitly warned:

> **"Stop and surface" check.** If you find the test passes against a fake handler but you're not sure the real route is hit: **STOP**. The URL bug existed precisely because the test bypassed the prefix.

What the dev shipped:

- `Vault__Spec__Writer` is an in-memory `dict` (mutable, but resets on every process boot — not a real vault).
- `Fast_API__Compute.py:158` wires it with `vault_attached=False` in production. **Every prod PUT returns 409.**
- The route test in `test_Routes__Vault__Spec.py` **mounts the route class without `prefix='/api/vault'`**, so it hits `/vault/spec/...` — exactly the prefix-bypass test bug the brief explicitly named as the antipattern.

The brief told the dev "STOP if you find this pattern." The dev did the pattern. The same review pass that wrote the brief is the same review pass that found it again. **This is not a knowledge gap; it's a discipline gap.**

The "fake-stub 2.0" name reflects the upgrade path: T2.4's predecessor (BV2.9) was a hardcoded `200` return. T2.4 replaced it with a real Python dict — superficially better — that still fails identically in production because the wiring sets `vault_attached=False` AND the route is never actually hit by the test.

---

## Per-phase verdicts

### Backend

| Phase | Verdict | Why |
|---|---|---|
| **T2.1** create_node podman + vnc | ✅ Solid | Generic service dispatch is real; podman + vnc work. |
| **T2.2** Firefox CLI | ✅ Solid (PARTIAL textbook) | 6 verbs shipped, `set-credentials` + `upload-mitm-script` deferred to T2.2b with brief filed. `(PARTIAL)` in commit subject. NotImplementedError points at brief. **The model phase for the new discipline.** |
| **T2.3** object=None + CI guard | ⚠ Has issues | Cleanup is real; guard is wired into `.github/workflows/ci-pipeline.yml:81-83` (closes previous audit gap). But: "Stop and surface" was bypassed — the dev silently expanded scope to add `linux` spec alias removal in `b515d2b` without authorisation. |
| **T2.4** real vault writer | 🔴 BLOCKING | Fake-stub 2.0; production wiring sets `vault_attached=False`; route test repeats the exact prefix-bypass bug the brief warned against. **Do not merge this as the resolution to the T2.4 brief.** |
| **T2.5** Lambda Web Adapter | ⚠ Has issues | Mangum imports gone; entry-point unchanged. But the Dockerfile delta + the AWS Lambda Web Adapter extension layer add aren't in the commit — verify in CI before declaring done. No PARTIAL flag despite incomplete delivery. |
| **T2.6** Safe_* primitives | ⚠ Silent scope cut | Sweep covered ~10% of brief. **`Pod__Manager` was named in the brief and untouched.** Spec-side raw `: str` / `: int` untouched. No PARTIAL flag, no T2.6b filed. |
| **T2.7** strip docstrings | ⚠ Commit lies | Missed 8 docstrings: 6 in `Cli__Firefox.py` (T2.2 added them 14 min earlier; same dev, same session) + 2 in playwright service. Commit claims "all CLI and spec files". |

### Frontend

| Phase | Verdict | Why |
|---|---|---|
| **T2.1** launch flow 3 modes | ⚠ PARTIAL honest, 2 hidden bugs | Textbook playbook for PARTIAL: 4 of 5 brief items shipped, AMI picker is a flagged placeholder, `BV__ami-list-endpoint.md` follow-up filed. **But:** (a) `ami_name` collected by `getValues()` is DROPPED on submit by `sg-compute-launch-panel._launch()` — silent data-loss for BAKE_AMI users; (b) `creation_mode` uses kebab-case (`bake-ami`, `from-ami`) which won't match the underscored enum values T2.6 will/should produce on the backend. |
| **T2.2** sg-compute-spec-detail | ⚠ Over-claimed | Structurally complete (manifest panel renders) but four real gaps under "COMPLETE": (a) card-body click not wired (only secondary "View details" button); (b) README link ships as known-broken anchor instead of placeholder + follow-up brief; (c) snapshot test omitted, not acknowledged; (d) no smoke screenshot. T2.1 had the playbook in front of it; T2.2 used half of it. |

---

## Process-rule application audit

The new rules from the v0.2.1 hotfix bundle:

| Rule | T2.1 BE | T2.2 BE | T2.3 BE | T2.4 BE | T2.5 BE | T2.6 BE | T2.7 BE | T2.1 FE | T2.2 FE |
|---|---|---|---|---|---|---|---|---|---|
| `PARTIAL` flag when scope cut | n/a | ✅ | n/a | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Follow-up brief filed for descope | n/a | ✅ T2.2b | n/a | ❌ | ❌ | ❌ | ❌ | ✅ BV__ami | ❌ |
| Live smoke test (auditable) | ❓ | ❓ | ❓ | ❌ | ❌ | ❓ | ❓ | ❌ no screenshot | ❌ no screenshot |
| Commit message matches content | ✅ | ✅ | ⚠ silent expansion | ⚠ "real writer" | ⚠ Dockerfile not in commit | ⚠ implies wide sweep | ❌ "all" but missed 8 | ✅ | ❌ COMPLETE wrong |
| "Stop and surface" rule | ✅ | ✅ | ❌ silent linux-removal expansion | ❌ shipped fake-stub the brief warned against | n/a | ❌ shipped 10% silently | ❌ shipped lying commit msg | ✅ | ❌ shipped over-claim |
| Debrief filed | ✅ | ❓ | ❓ | ❌ | ❌ | ❌ | ❌ | ❓ | ✅ (but says COMPLETE wrongly) |

**Score:** 9 phases × ~6 rules = ~54 datapoints. ~12 ✅, ~24 ❌, ~14 ❓ (not auditable). The rules **work** (T2.2 BE + T2.1 FE prove it). They were **not applied uniformly**.

The pattern of bypass: when the phase is genuinely small + clean (T2.1 BE), no need for PARTIAL. When the phase is small + clean (T2.2 BE, T2.1 FE), PARTIAL is used correctly. When the phase is large + the dev finds it harder than expected, the "Stop and surface" rule loses to "ship something and move on." **The discipline gap is in the harder phases.**

---

## Recommended path forward

### Step 1 — Block before T3 starts

Same shape as the previous round. Don't start any T3 work until:

1. **T2.4b** — real vault writer that:
   - Has `vault_attached=True` wired in production paths.
   - Has a route test that uses `prefix='/api/vault'` and hits the real URL.
   - Returns `Schema__Vault__Spec__Write__Receipt` from the route, not raw dicts.
   - Round-trip test writes 1KB, reads back, asserts SHA256 matches.

2. **T2.6b** — finish the primitives sweep:
   - `Pod__Manager` — was explicitly named in the T2.6 brief. Touch it.
   - All spec-side raw `: str` / `: int` parameters in service classes.
   - Confirm `node_name` (was `stack_name`) field rename.
   - Updated CI guard to forbid raw primitives in new schema/service code.

3. **T2.7b** — finish the docstring sweep:
   - The 6 docstrings in `Cli__Firefox.py` (added by T2.2 itself).
   - The 2 in playwright service.
   - Sweep the entire backend tree, not just `cli/`.

4. **FE patch** — one PR covering:
   - T2.1 `ami_name` plumbing fix (don't drop it on submit).
   - T2.1 `creation_mode` enum-case alignment (kebab → underscore to match backend).
   - T2.2 card-click wiring.
   - T2.2 flip the debrief to PARTIAL; file `BV__spec-readme-endpoint.md` for the README link.
   - Snapshot tests for the 5 launch-form modes + spec-detail.
   - Browser smoke screenshot in PR description.

### Step 2 — Backfill missing debriefs

6 of 7 backend T2 phases have no debrief. Backfill them. Each one explicitly classifies:

- **Good failures:** caught by tests, surfaced early. (T2.3 CI guard wiring discovered the missing workflow step is a good failure — name it.)
- **Bad failures:** silent scope cuts, "Stop and surface" bypasses, commit-message lies. **These three phases are bad failures by the new debrief vocabulary** — name them.

Without classification, the lessons don't propagate.

### Step 3 — Calibrate, then resume

Have a 5-minute conversation with the backend dev (the one who shipped T2.4):

> "T2.4 is exactly what the brief told you not to do. The brief named the antipattern by name; you shipped it anyway. The fix is one PR. But before that fix, I want to understand: when you read the brief and started writing the in-memory dict, did the 'Stop and surface' check fire and you ignored it, or did the rule not register? Because if it didn't register, we have a tooling problem (the rule is in the brief but not in your loop). If it fired and you ignored it, we have a discipline conversation."

This is the exact "stop and surface" conversation the rule is supposed to enable. Without it, T3 will compound.

The frontend dev's pattern is different — they're not bypassing rules, they're **forgetting the rules under load.** T2.1 was textbook; T2.2 used half of it; the fix is a checklist (PARTIAL? follow-up? smoke screenshot?) on every PR.

---

## New briefs to file (in priority order)

| # | Path | Owner | Blocks |
|---|---|---|---|
| **T2.4b** | `team/comms/briefs/v0.2.1__hotfix/backend/T2_4b__real-vault-writer-finish.md` | BE | All vault consumers |
| **T2.6b** | `team/comms/briefs/v0.2.1__hotfix/backend/T2_6b__safe-str-primitives-finish.md` | BE | T3.x cleanups that touch Pod__Manager |
| **T2.7b** | `team/comms/briefs/v0.2.1__hotfix/backend/T2_7b__strip-docstrings-finish.md` | BE | None (cosmetic) |
| **T2-FE-patch** | `team/comms/briefs/v0.2.1__hotfix/frontend/T2_patch__ami-and-spec-detail-fixes.md` | FE | None — runtime UX |
| **BV__spec-readme-endpoint** | `team/comms/briefs/v0.2.1__hotfix/backend/BV__spec-readme-endpoint.md` | BE | T2-FE-patch's README fix |

The user already has `BV__ami-list-endpoint.md` filed by the FE dev — model for the others.

---

## Solid wins (don't lose these in the rework)

- **T2.2 BE PARTIAL discipline is the model.** The commit subject says `(PARTIAL)`. The deferred verbs raise `NotImplementedError` pointing at the follow-up brief. T2.2b was filed in the same PR. Replicate this everywhere.
- **T2.3 CI guard wired** into `.github/workflows/ci-pipeline.yml:81-83`. The previous audit's gap (guard exists but isn't invoked) is closed.
- **T2.1 FE textbook PARTIAL** + follow-up brief filed for the unblocking endpoint. Frontend's discipline beats backend's on this round.
- **T2.1 BE generic service dispatch** — clean architecture; works for podman + vnc; sets the pattern for the remaining 8 specs.

---

## Bottom line

The new process rules **work**. T2.2 BE and T2.1 FE prove it. The team is **not yet uniformly applying them** — the application correlates with phase difficulty (easier phase → rule applied; harder phase → rule bypassed under pressure).

The fix is **conversation + checklist**, not new rules. The rules are right. They just need to be the muscle-memory default rather than the optional discipline.

Once T2.4b ships and the missing debriefs are backfilled, T3.x can start. **Do not start T3 with T2.4 broken in production.** The vault writer is a foundation for downstream specs (firefox MITM scripts, S3 call-log archives) — every consumer that builds on top will silently fail at the first PUT.
