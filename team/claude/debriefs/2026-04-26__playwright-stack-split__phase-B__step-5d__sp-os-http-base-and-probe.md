# Phase B · Step 5d — `sp os` HTTP base + probe

**Date:** 2026-04-26.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Branch:** `claude/refactor-playwright-image-FVPDf`.
**Predecessor:** Step 5c (AWS helpers).

---

## What shipped

Two small focused HTTP files (one class per file, single responsibility):

| File | Lines | Role |
|---|---|---|
| `OpenSearch__HTTP__Base.py` | ~40 | Request seam — wraps `requests` with `verify=False`, Basic auth, scoped urllib3 warning suppression |
| `OpenSearch__HTTP__Probe.py` | ~35 | Read-only probes — `cluster_health()` (returns `{}` on any failure; populates `-1` sentinels) and `dashboards_ready()` (True on 2xx) |

Mutations (`delete_index`, `bulk_post`, etc.) are **not** here — they belong in their own helper files when the service surface needs them.

## Tests

**14 new tests across two focused files:**

`test_OpenSearch__HTTP__Base.py` (5 tests):
- defaults (`verify=False`, `timeout=DEFAULT_TIMEOUT`)
- `request()` passes through `verify=False` + default timeout, no auth when no creds
- Basic auth attached when creds provided
- custom timeout honoured
- headers + data forwarded

`test_OpenSearch__HTTP__Probe.py` (9 tests):
- `cluster_health` 200 returns parsed body
- non-200 returns `{}`
- network error returns `{}`
- non-JSON body returns `{}` (defensive against nginx-502 HTML)
- trailing-slash on base_url stripped (no `//` in path)
- `dashboards_ready` 2xx ⇒ True (200/201/204/299)
- non-2xx ⇒ False (300/401/403/500/502)
- network error ⇒ False
- forwards Basic auth

**Pattern:**
- `_Fake_HTTP(OpenSearch__HTTP__Base)` is a real subclass that overrides `request()` to return scripted `_Fake_Response` objects. **No `unittest.mock`, no `MagicMock`, no `patch`.**
- The `Base` test substitutes `requests.request` directly via attribute swap (matches Phase A step 3b's monkey-patch pattern).

## Test outcome

| Suite | Before (5c) | After (5d) | Delta |
|---|---|---|---|
| Full `tests/unit/` | 1299 passed | 1313 passed | +14 |

Same 1 unchanged pre-existing failure.

## File-size discipline

| File | Lines |
|---|---|
| `OpenSearch__HTTP__Base.py` | 40 |
| `OpenSearch__HTTP__Probe.py` | 35 |
| `test_OpenSearch__HTTP__Base.py` | ~75 |
| `test_OpenSearch__HTTP__Probe.py` | ~110 |

For comparison, `Elastic__HTTP__Client.py` is 169 lines, single file, 6 methods.

## What was deferred

- Index ops (`delete_index`, `create_index`, `index_exists`) — into a future `OpenSearch__HTTP__Index__Helper`
- Bulk ops (`bulk_post`) — into a future `OpenSearch__HTTP__Bulk__Helper`
- Saved-object ops (dashboard import/export) — into `OpenSearch__HTTP__Saved_Objects__Helper`

These land when the service or dashboard generator needs them.

## Next

Phase B step 5e — `OpenSearch__Service` orchestrator (`launch_instance`, `create_stack`, `list_stacks`, `get_stack_info`, `delete_stack`, `health`). Composes the AWS helpers (5c) + HTTP probe (5d).
