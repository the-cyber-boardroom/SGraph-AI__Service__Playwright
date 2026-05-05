# Backend v0.2.1 finish session — paste into a fresh Claude Code session

You are the **v0.2.1 finish backend** team for SG/Compute. The v0.2.1 hotfix bundle is closed; this session ships the remaining 6 phases of the original v0.2.0 forward roadmap and produces the v0.2.1 release artefact.

## Status as of 2026-05-05 (latest)

**Hotfix bundle: closed.** T1 + all T2 patches + T3 cleanups + 3 BV briefs (ami-list, caller-ip, spec-readme) all shipped. The discipline pattern is muscle memory now — keep going.

**6 phases remain on the v0.2.0 forward roadmap.** All briefs already written; located at `team/comms/briefs/v0.2.0__sg-compute__backend/BV2_*.md`.

## Recommended order

```
BV2.17  →  BV2.13  →  BV2.14  →  BV2.15  →  BV2.16  →  BV2.18
```

Why this order:
1. **BV2.17** is smallest — delete `/containers/*` sidecar aliases. Frontend FV2.8 already verified zero callers. Quick warm-up.
2. **BV2.13** + **BV2.14** raise the spec quality bar before any public publish.
3. **Architect locks ratified 2026-05-05** — see [`../architect-locks.md`](../architect-locks.md). Lock 1 (cookie `HttpOnly=true`) ✅ approved. Lock 2 (CORS allowlist) ⏸ deferred to v0.3. **BV2.15 is scoped down accordingly** — cookie hardening only; do NOT touch CORS config.
4. **BV2.15** — cookie `HttpOnly=true` + auth test coverage. Pair with FE smoke test (cookie change risks the iframe pattern).
5. **BV2.16** — storage spec discovery test. Validates the cross-repo s3_server install.
6. **BV2.18** — final phase. TestPyPI wheels + `RELEASE.md` = the v0.2.1 release artefact.

## Read in this order

1. `team/humans/dinis_cruz/claude-code-web/05/05/14/00__executive-review__T2-implementation.md` — full context (Tier 4 process rules)
2. `team/comms/briefs/v0.2.1__finish/00__README.md` — this bundle's overview
3. `team/comms/briefs/v0.2.1__finish/architect-locks.md` — the 2 decisions blocking BV2.15
4. **Your phase brief** — pick from the order above; first one is `team/comms/briefs/v0.2.0__sg-compute__backend/BV2_17__delete-container-aliases.md`

## Hard rules (binding every PR)

- Type_Safe everywhere; no Pydantic; no Literals; no `: object = None`.
- One class per file; empty `__init__.py`.
- Routes have no logic; pure delegation.
- `osbot-aws` for AWS — no direct boto3.
- **No mocks, no patches** in tests under `sg_compute__tests/`.
- 80-char `═══` headers; no docstrings.
- Update reality doc + `team/roles/librarian/reality/changelog.md` in same commit.

## Process rules (the new discipline)

- **`(PARTIAL)` in commit subject** if you descope.
- **Follow-up brief filed in same PR** when you defer scope.
- **CI guards wired in same PR** they're added.
- **Live smoke test** as an acceptance gate — curl output or screenshot in PR description.
- **"Stop and surface"** if you find yourself working around a problem.
- **Commit message matches content** — `grep` to prove it.
- **Each PR ends with a debrief** in `team/claude/debriefs/`.
- **Bad failures named** — if a previous shipment had a flaw you're fixing, classify it as a bad failure in the new debrief (the T2.4b debrief is the model).

## Your first task

**BV2.17** — delete `/containers/*` sidecar aliases. The brief is at `team/comms/briefs/v0.2.0__sg-compute__backend/BV2_17__delete-container-aliases.md`. Frontend already verified zero callers in FV2.8. Should be a tight, one-file deletion + tests.

**Stop after BV2.17 ships.** Wait for the human to ratify and tell you which phase to do next. Do NOT auto-pick BV2.13.

## Exit criterion (when v0.2.1 is done)

- All 6 phases shipped.
- TestPyPI wheels (`sg-compute` + `sg-compute-specs`) installable in a fresh venv.
- `sg-compute spec list` works against the installed catalogue.
- `RELEASE.md` documents the publish workflow.
- `team/comms/briefs/archive/v0.2.1__hotfix/` exists with closing-commit hash.

After that, v0.3 planning begins — see `00__README.md` "deferred to v0.3" list.

---

Begin by reading the four files in section "Read in this order" above, then BV2.17. Ship one PR. Wait.
