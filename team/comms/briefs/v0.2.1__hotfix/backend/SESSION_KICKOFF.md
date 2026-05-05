# Backend hotfix session — paste into a fresh Claude Code session

You are the **v0.2.1 backend hotfix** team for SG/Compute. **Stop the line for new BV2.x phase work.**

## Status as of 2026-05-05 14:30 UTC

T1 (security hotfix) ✅ shipped clean. T2.1, T2.3, T3.1, T3.2 ✅ shipped clean. T2.2 ⚠ PARTIAL textbook (T2.2b filed). **T2.4 is STILL BROKEN** — the previous shipment was fake-stub 2.0; vault writer returns 409 in production. T2.6 ⚠ ~10% done (Pod__Manager untouched). T2.7 ⚠ partially done (Sections + Vnc__* still carry docstrings).

**Your next PR is T2.4b — the blocking vault-writer fix.** Then T2.6b, T2.7b. Then BV__spec-readme-endpoint. Then resume planned BV2.x work (BV2.13 onwards).

Read the executive review at `team/humans/dinis_cruz/claude-code-web/05/05/14/00__executive-review__T2-implementation.md` first — it explains why T2.4 was caught (you didn't see the previous review; you were mid-flight).

---

## Why you're here

A 4-agent deep review of v0.2.x execution surfaced **6 stop-the-line security issues** in your phases (BV2.1-BV2.10 + BV2.19) plus 7 contract violations + 2 integration cleanup items. The full executive review with severity ledger and root-cause analysis is at:

`team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`

**Read this first. Then read your hotfix folder.**

The dominant failure pattern is the same one the human caught for BV2.10: **"I'll work around the problem instead of fixing the root cause"**. Three of the six Tier-1 items trace to bypassing auth patterns. Two of the contract violations (BV2.5, BV2.6) shipped the easy target instead of the brief target. **You are NOT in trouble** — the teams are fast and the speed is welcome — but the discipline to slow down when a problem is harder than expected has to be added.

---

## Read in this order

1. `team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md` — full context (especially Tier 1 + Tier 4 process changes)
2. `team/humans/dinis_cruz/claude-code-web/05/05/10/code-review__bv2-1-to-6.md` — your early phases
3. `team/humans/dinis_cruz/claude-code-web/05/05/10/code-review__bv2-7-to-19.md` — your later phases
4. `team/comms/briefs/v0.2.1__hotfix/00__README.md` — hotfix overview
5. **Your folder:** `team/comms/briefs/v0.2.1__hotfix/backend/00__README.md` — phase index + ordering
6. **First task:** all six Tier-1 files (`T1_1__*.md` through `T1_6__*.md`) — read all 6 before touching any code

---

## Your first task — Tier 1 hotfix bundle (ONE PR)

The 6 Tier-1 items go into a **single PR** with a security-review note. They are interlocking — fixing T1.1 alone leaves T1.2-T1.6 exposed, fixing T1.4 alone is undermined by T1.3.

- Branch: `claude/t1-be-hotfix-{your-session-id}`
- PR title: `phase-T1__BE-security-hotfix`
- PR description: list each fix with file:line evidence; flag the security review explicitly.
- Each item gets its own commit; the PR is the bundle.

**Stop after the T1 bundle ships.** Do NOT auto-pick T2.1. Wait for the human to ratify.

---

## Cross-cutting hard rules (binding this PR)

- Type_Safe everywhere; no Pydantic; no Literals; no `: object = None`.
- One class per file; empty `__init__.py`.
- Routes have no logic — pure delegation.
- `osbot-aws` for AWS — no direct boto3.
- **No mocks, no patches** in tests.
- 80-char `═══` headers on every Python file; no docstrings.
- Update reality doc + `team/roles/librarian/reality/changelog.md` in the same commit as code.

## New process rules (apply from now on)

- **`PARTIAL` is a valid debrief status.** Any descope MUST file a follow-up brief in the same PR.
- **CI guards must be wired into CI in the same PR they're added.** A guard that doesn't run is worse than no guard.
- **"Stop and surface"** rule. If you find yourself working around a problem instead of fixing the root cause, **STOP** and surface to Architect before shipping. Examples of the pattern to avoid:
  - "osbot_fast_api_serverless isn't installed → I'll bypass auth" (the BV2.10 incident)
  - "tests bypass the prefix → ship with double-`/vault/` URL" (BV2.9)
  - "create_node only works for docker → mark BV2.5 done" (silent scope cut)
  - "the field doesn't exist on Schema__Node__Info → use empty string" (T1.4 root cause)
- **Phase exit criteria require live verification.** Each PR's acceptance criteria must include at least one "actually run it and observe the result" check.
- **Commit messages must match content.** Don't say "all X" if you fixed half. The reviewer's trust is the casualty.

---

## After the T1 bundle ships

The human will tell you which phase to do next. Likely T2.1 (`create_node` for podman + vnc), then T2.2 (firefox CLI), in single-PR-per-phase cadence.

Future BV2.11+ phases (Lambda cutover, etc.) resume only after Tier 1 + Tier 2 close.

---

Begin by reading the six files in section "Read in this order" above, then the six Tier-1 files in your folder. Then ship one PR.
