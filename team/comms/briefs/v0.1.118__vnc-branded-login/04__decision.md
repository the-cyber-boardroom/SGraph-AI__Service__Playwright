# 04 — Decision (TBD)

Owner picks ONE of the five options from `00__README.md` and notes the
choice + rationale here, then this folder gets promoted into a real
implementation slice (`v0.1.NNN__vnc-branded-login`) under
`team/comms/plans/`.

## Recommendation (one-liner)

**Option 1 — FastAPI auth sidecar** — fits the project's Python /
`Type_Safe` patterns, half-day of work, fully solves the iframe pain,
keeps the door open for OAuth later.

## Decision rubric

| Criterion | Weight |
|---|---|
| Half-day or less of dev work | high |
| No new external dependency | high |
| Works for ephemeral, throwaway stacks (no DNS / IAM / CF setup per stack) | high |
| Branded login page | high |
| Iframe-friendly (cookie based) | high |
| Removes the self-signed-cert prompt | medium (Option 2 wins this) |
| Path to MFA / OIDC later | medium |
| Audit log | low (every option can do this) |

Score the five options against this in the meeting; expected outcome is
Option 1 unless we already plan to swap nginx for Caddy for unrelated
reasons (then Option 2).

## Out of scope for this brief

- Per-user accounts (right now there's exactly one user, "operator").
  When/if we want named users, extend the sidecar to read a YAML of
  users; the cookie payload already has a `user` field.
- Password reset flows. Throw away the EC2 and `sp vnc create` again.
- Federation. Add an OAuth handler to the same sidecar later.
