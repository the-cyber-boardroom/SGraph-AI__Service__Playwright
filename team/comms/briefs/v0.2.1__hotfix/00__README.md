# v0.2.1 Hotfix — Tier-1 / Tier-2 / Tier-3 Findings

**Date:** 2026-05-05
**Source review:** [`team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md)
**Status:** PROPOSED — share with each dev before they start their next session.

---

## Why this folder exists

The 4-agent deep review of v0.2.x execution (58 commits since v0.2.0) surfaced **7 stop-the-line security issues**, **13 contract violations**, and **11 integration cleanup items**. Several of these have the same shape as the BV2.10 auth-bypass the human caught — workarounds shipped instead of root-cause fixes.

**Both teams stop new BV2.x / FV2.x phase work until Tier 1 is closed.**

---

## Where to read

Each dev gets their own folder. Self-contained:

- [`backend/`](backend/) — backend dev. 6 Tier-1 + 7 Tier-2 + 2 Tier-3.
- [`frontend/`](frontend/) — frontend dev. 1 Tier-1 + 5 Tier-2 + 5 Tier-3.

Each team folder has:

- `00__README.md` — phase index, severity, ordering
- `SESSION_KICKOFF.md` — pasteable into a fresh Claude Code session
- `T1_*__*.md` — Tier-1 hotfix items
- `T2_*__*.md` — Tier-2 contract-violation patches (one per item)
- `T3_*__*.md` — Tier-3 integration cleanup items

---

## Recommended message to send each dev

> Please read [`team/comms/briefs/v0.2.1__hotfix/{backend|frontend}/00__README.md`](backend/00__README.md) and the executive review at [`team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md). Ship the Tier-1 items as **one PR with a security review note** before any other work. Then ship Tier-2 items one PR each, in the order in `00__README.md`.

---

## Cross-cutting process changes (apply to both teams from now on)

These should be added to `team/comms/briefs/v0.2.0__sg-compute__architecture/00__README.md` cross-cutting rules in the same hotfix window:

1. **`PARTIAL` is a valid debrief status.** Any phase that descopes MUST file a follow-up brief in the same PR.
2. **CI guards must be wired into CI in the same PR they're added.** A guard that doesn't run is worse than no guard — false confidence.
3. **"Stop and surface" rule.** If you find yourself working around a problem instead of fixing the root cause (e.g. "the library isn't installed, I'll bypass it"), STOP. Surface to Architect before shipping.
4. **Phase exit criteria require live verification, not grep counts.** Each phase brief MUST include a "live smoke test" acceptance criterion.
5. **Commit messages must match commit content.** Don't say "all X" if you fixed half. The reviewer's trust is the casualty.

---

## Severity legend

- 🔴 **Tier 1** — STOP THE LINE. Security / runtime breakage. Fix as one PR with security review.
- ⚠ **Tier 2** — Contract violation. Silent scope cut, fake stub, project-rule violation. Fix as separate PRs.
- ⚠ **Tier 3** — Integration cleanup. Lower severity but real coupling problems. Fix incrementally.
- ⚠ **Tier 4** — Process changes (above) — bake into the working agreement.

---

## Solid wins (don't break these)

The exec review called out these as genuinely good — preserve them while patching:

- FV2.1 (state vocabulary) — `shared/node-state.js` is exactly right; tolerant of legacy values.
- FV2.3 catalogue loader — solid for the data layer.
- FV2.7 control-plane proxy on the wire — URL pattern correct; iframe ops correctly stay direct.
- FV2.8 verification — clean grep sweep with documented exceptions.
- BV2.10 fix itself (commit `54f349f`) — the auth-bypass attempt was caught and corrected.
- Three-file pattern + SgComponent base — uniform across 30+ web components.
- Event-vocabulary spec was published.

When patching, do not regress these.
