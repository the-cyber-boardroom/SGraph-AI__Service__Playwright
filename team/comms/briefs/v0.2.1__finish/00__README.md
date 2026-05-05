# v0.2.1 finish — close out the v0.2.x forward roadmap

**Status:** PROPOSED — share with each dev for their next session.
**Predecessor:** [`v0.2.1__hotfix/`](../v0.2.1__hotfix/) — closed (T2.2b is the only remaining item, deferred as a feature add).
**Source plan:** [`team/comms/briefs/v0.2.0__sg-compute__backend/00__README.md`](../v0.2.0__sg-compute__backend/00__README.md) — the original BV2.13-BV2.18 phase index. Briefs already exist; this folder is a kickoff + sequencing layer.

---

## Why this folder exists

The v0.2.1 hotfix bundle is effectively closed. **6 phases remain on the original v0.2.0 backend roadmap** (BV2.13-BV2.18) — all unblocked, all small, all with briefs already written. This bundle ships them and produces the v0.2.1 release artefact (TestPyPI wheels + RELEASE.md).

The frontend has a small verification + smoke-test role. No new FV phase work in v0.2.1; FV2.13 (dashboard move) and the visual snapshot pattern are deferred to v0.3.

---

## What's left (one-line per phase)

### Backend — 6 phases (one PR each)

| # | Brief | Theme | Architect lock? |
|---|-------|-------|------------------|
| BV2.17 | [`BV2_17__delete-container-aliases.md`](../v0.2.0__sg-compute__backend/BV2_17__delete-container-aliases.md) | Delete `/containers/*` sidecar aliases (FV2.8 verified zero refs) | — |
| BV2.13 | [`BV2_13__spec-layout-normalisation.md`](../v0.2.0__sg-compute__backend/BV2_13__spec-layout-normalisation.md) | Normalise all 12 specs to canonical layout; lock `Enum__Spec__Capability` header | — |
| BV2.14 | [`BV2_14__spec-test-coverage.md`](../v0.2.0__sg-compute__backend/BV2_14__spec-test-coverage.md) | Add Routes + Service tests to every spec; drop any remaining `unittest.mock.patch` | — |
| BV2.15 | [`BV2_15__sidecar-security-hardening.md`](../v0.2.0__sg-compute__backend/BV2_15__sidecar-security-hardening.md) | Cookie `HttpOnly=true`; CORS origin allowlist; `Routes__Host__Auth` test coverage | **YES** — see [`architect-locks.md`](architect-locks.md) |
| BV2.16 | [`BV2_16__storage-spec-integration.md`](../v0.2.0__sg-compute__backend/BV2_16__storage-spec-integration.md) | Storage spec category + `s3_server` cross-repo discovery test | — |
| BV2.18 | [`BV2_18__testpypi-publish.md`](../v0.2.0__sg-compute__backend/BV2_18__testpypi-publish.md) | TestPyPI publish + `RELEASE.md` | — |

### Frontend — verification role (no new FV phases)

The frontend's role in v0.2.1 finish is **defensive verification**, not new feature work:

- After **BV2.15** (cookie `HttpOnly=true`) — verify the iframe pattern still works in browser (Terminal tab + Host API tab).
- After **BV2.17** (alias delete) — re-confirm zero `/containers/*` references in the dashboard (FV2.8's grep gate).
- Before **BV2.18** (TestPyPI publish) — full dashboard smoke test against the soon-to-be-released wheel.

See [`frontend/SESSION_KICKOFF.md`](frontend/SESSION_KICKOFF.md).

---

## Recommended sequence (one PR per phase)

```
BV2.17  →  BV2.13  →  BV2.14  →  [Architect locks]  →  BV2.15  →  FE smoke  →  BV2.16  →  FE smoke  →  BV2.18
```

Why this order:

1. **BV2.17 first** — smallest cleanup; FV2.8 already verified the precondition; quick win to start the streak.
2. **BV2.13 + BV2.14** — quality bar before any public publish. No external dependency.
3. **Architect locks** for BV2.15 must land before that phase opens — see `architect-locks.md`. Two small decisions.
4. **BV2.15** — security hardening; FE smoke test gate immediately after (the iframe pattern depends on the cookie).
5. **BV2.16** — storage spec discovery test; validates the cross-repo extraction worked.
6. **BV2.18** — final phase; TestPyPI publish + RELEASE.md = v0.2.1 release artefact.

Estimated cadence: 6 backend sessions + 2-3 frontend smoke tests = ~1 week of work at the team's current pace.

---

## What's deferred to v0.3 (don't pick these up)

- FV2.13 dashboard move (`sg_compute/frontend/`)
- `FV__live-visual-snapshot-pattern.md` (Playwright-Node visual snapshot)
- Storage spec category formalisation
- Operation-mode taxonomy generalisation (FULL_LOCAL/PROXY/HYBRID/SELECTIVE)
- Cross-repo extraction policy formalisation
- Per-spec independent PyPI publishing
- Multi-platform routing (`k8s/`, `local/`, `gcp/`)
- LETS subsystem migration
- Repo extraction to `sgraph-ai/SG-Compute`
- T2.2b Firefox CLI deferred verbs (feature add; could ride v0.3 firefox-track)

---

## Process rules (binding every phase)

Same as the hotfix bundle — these are now muscle memory:

- **`PARTIAL` if you descope** — and file the follow-up brief in the same PR.
- **CI guards wired in same PR** as added.
- **"Stop and surface"** if you find yourself working around a problem.
- **Live smoke test** in PR description (browser screenshot or curl output).
- **Commit message matches content** — no "all X" claims unless `grep` proves it.
- **Each PR ends with a debrief** in `team/claude/debriefs/`.

---

## When v0.2.1 is done

- All 6 BV phases shipped.
- TestPyPI wheels installable in a fresh venv.
- `RELEASE.md` documents the publish workflow.
- Frontend smoke tests recorded in PR descriptions.
- v0.2.1 release notes drafted (covers everything since v0.2.0).
- The hotfix bundle moves to `team/comms/briefs/archive/v0.2.1__hotfix/` with closing-commit hash.

Then v0.3 planning starts — see "deferred to v0.3" list above for the agenda.
