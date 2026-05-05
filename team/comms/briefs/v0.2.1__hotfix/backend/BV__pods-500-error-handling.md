# BV — Pods Route 500 Error Handling

**Date:** 2026-05-05
**Priority:** HIGH — pods tab is completely unusable; returns 500 on any node that can't be reached

---

## Problem

`Routes__Compute__Pods.list_pods()` delegates to `Pod__Manager.list_pods()` with no exception handling:

```python
def list_pods(self, node_id: str) -> dict:
    return self.manager.list_pods(node_id).json()
```

`Pod__Manager._resolve_api_key()` reads from SSM. If:
- SSM credentials are absent
- The SSM path does not exist (CLI-launched node, key never stored via dashboard)
- The sidecar is unreachable (instance still booting, wrong IP)

…an exception propagates and FastAPI returns a raw 500. The dashboard shows a generic error with no actionable information.

---

## Fix

Wrap the route handler in try/except and return a structured error response:

```python
from fastapi import HTTPException

def list_pods(self, node_id: str):
    try:
        return self.manager.list_pods(node_id).json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"sidecar unreachable for node {node_id}: {e}"
        )
```

Apply the same pattern to all other pod-route handlers that call the manager (`get_pod`, `create_pod`, `delete_pod`, `get_pod_logs`, etc.) — any unguarded `self.manager.*` call can raise.

---

## Error display in the dashboard

The `sg-compute-nodes-view` pods tab already reads the response and shows an error message when the fetch fails. A 503 with a descriptive `detail` field gives the UI enough to render a useful message like:

> "Sidecar unreachable — node may still be starting up"

instead of an opaque "500 Internal Server Error".

---

## Acceptance criteria

1. `GET /api/nodes/{node_id}/pods` for an unreachable sidecar returns 503 (not 500).
2. Response body has `{ "detail": "sidecar unreachable for node …: …" }`.
3. Dashboard pods tab renders the error message rather than a blank or raw 500.
4. CI test: mock an unreachable sidecar; assert 503 + detail field present.

---

## Related

- `BUG-BATCH-1__sidecar-auth-and-terminal.md` — full analysis doc (Bug 2)
