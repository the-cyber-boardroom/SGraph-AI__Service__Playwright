# Debrief — Bug Batch 1: Sidecar Auth and Terminal Failures

**Date:** 2026-05-05
**Branch:** `claude/sgcompute-frontend-v0.2-5sjIO`
**Commit:** (backfill by Historian)
**Status: ANALYSIS COMPLETE — backend fixes pending**
**Brief:** `team/comms/briefs/v0.2.1__hotfix/frontend/BUG-BATCH-1__sidecar-auth-and-terminal.md`

---

## Summary

User reported 5 runtime bugs via screenshots after loading the admin dashboard against a CLI-launched node. All 5 bugs share a common root: when a node is created via `sp docker create` the dashboard has no way to obtain the host API key. Root causes identified; backend briefs filed; no frontend code changes required (frontend is already correct).

---

## Bugs Investigated

### Bug 1 — Boot log 401
- `_fetchBootLog()` in `sg-compute-nodes-view` sends `X-API-Key` header only when key is non-empty.
- For CLI-launched nodes `host_api_key` is empty in the stack object → no header → 401.
- **Resolution:** blocked on Bug 4 backend fix.

### Bug 2 — Pods tab 500
- `Routes__Compute__Pods.list_pods()` has no try/except.
- `Pod__Manager._resolve_api_key()` throws when SSM is inaccessible or path absent → unhandled → 500.
- **Resolution:** `BV__pods-500-error-handling.md` filed.

### Bug 3 — rbash error in terminal iframe
- Sidecar spawns `/bin/rbash`. Ubuntu EC2 AMIs do not ship `rbash` → exec fails → iframe shows error.
- **Resolution:** `BV__sidecar-rbash-fix.md` filed.

### Bug 4 — CLI-launched nodes have no API key in dashboard
- `Schema__Node__Info` exposes `host_api_key_ssm_path` but NOT the key value.
- Dashboard capture (`sp-cli:node.launched` event) only fires for dashboard-launched nodes.
- **Resolution:** `BV__host-api-key-via-ec2-tag.md` filed. Interim fix: tag EC2 instance with key at creation; expose via `GET /api/nodes`. Approved as acceptable risk by Dinis Cruz 2026-05-05.

### Bug 5 — Quick-commands "Authentication failed" + unusual layout
- Direct consequence of Bug 4 (no key → all sidecar calls unauthenticated).
- The terminal iframe layout (iframe above, commands below) is correct — it only looks odd because the iframe shows the rbash error (Bug 3).
- **Resolution:** Resolved by Bug 4 fix + Bug 3 fix.

---

## Dependency Graph

```
Bug 4 → fixes Bug 1, Bug 5 (auth)
Bug 3 → fixes Bug 5 (iframe usable)
Bug 2 → independent; improves error UX
```

---

## Documents Filed

| Document | Path |
|----------|------|
| Bug analysis | `team/comms/briefs/v0.2.1__hotfix/frontend/BUG-BATCH-1__sidecar-auth-and-terminal.md` |
| Backend brief: EC2 tag | `team/comms/briefs/v0.2.1__hotfix/backend/BV__host-api-key-via-ec2-tag.md` |
| Backend brief: pods 500 | `team/comms/briefs/v0.2.1__hotfix/backend/BV__pods-500-error-handling.md` |
| Backend brief: rbash | `team/comms/briefs/v0.2.1__hotfix/backend/BV__sidecar-rbash-fix.md` |

---

## Frontend Changes

None. The frontend code in `admin.js` and `sg-compute-nodes-view` already handles `host_api_key` correctly — it uses `_hostApiKeys[s.node_id] || s.host_api_key || ''`. Once the backend returns the key in the node payload the dashboard will work without any frontend changes.

---

## Good/Bad Failures

**Good failure:** All 5 bugs are direct consequences of a single architectural gap (API key flow incomplete for CLI path) rather than scattered independent bugs. Identifying this unified root cause up front avoids duplicate backend PRs.

**Good failure:** The "acceptable risk" framing for the EC2 tag approach was surfaced and approved before implementation — not worked around silently.

**No bad failures this session** — pure investigation + documentation.
