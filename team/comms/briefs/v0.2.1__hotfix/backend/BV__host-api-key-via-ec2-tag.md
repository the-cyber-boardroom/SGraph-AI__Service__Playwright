# BV — Host API Key via EC2 Instance Tag

**Date:** 2026-05-05
**Priority:** HIGH — blocks boot-log auth, quick-commands auth, all direct sidecar calls from dashboard
**Security posture:** Acceptable risk (approved by Dinis Cruz 2026-05-05); PKI replacement deferred

---

## Problem

When a node is launched via CLI (`sp docker create`) the dashboard has no way to obtain the host API key. `Schema__Node__Info` only exposes `host_api_key_ssm_path`; `GET /api/nodes` returns that path but not the key value itself. Any dashboard feature that calls the sidecar directly (boot log, pods tab, quick commands) fails with 401.

---

## Agreed Solution — EC2 Tag + GET /api/nodes response field

### 1. Tag the EC2 instance at creation time

In `Node__Creator` (or wherever `ec2_client.create_instance()` is called), add an additional tag:

```python
{ 'Key': 'sg-compute:host-api-key', 'Value': host_api_key_value }
```

The key value is already generated at creation time (same value written to SSM). Tagging it is a one-line addition alongside the existing Name / spec_id / node_id tags.

**Security rationale:**
- The tag is readable only by IAM identities with `ec2:DescribeTags` permission on the instance.
- Reaching the node's sidecar already requires AWS credentials (security group restricts access).
- The tag value is valid only for the lifecycle of the instance — instance termination removes it.
- This is an interim measure; PKI/mTLS will replace it when the platform matures.

### 2. Read the tag in `GET /api/nodes` and expose the key

In the node-list or node-info builder, resolve the tag value alongside other instance metadata and populate `Schema__Node__Info.host_api_key`:

```python
# pseudo-code
tags   = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
key    = tags.get('sg-compute:host-api-key', '')
info   = Schema__Node__Info(
    ...existing fields...,
    host_api_key = key,
)
```

### 3. Add `host_api_key` field to `Schema__Node__Info`

```python
class Schema__Node__Info(Type_Safe):
    ...
    host_api_key_ssm_path : Safe_Str__SSM__Path = Safe_Str__SSM__Path()
    host_api_key          : Safe_Str            = Safe_Str()           # NEW
```

Use `Safe_Str` (or `Safe_Str__Api__Key` if that primitive exists).

---

## Frontend impact

`admin.js` `_populatePanes()` already contains:
```js
host_api_key: _hostApiKeys[s.node_id] || s.host_api_key || ''
```

So the moment `GET /api/nodes` returns `host_api_key` in each node object, the frontend will use it automatically for boot-log auth, pod list calls, and quick-commands — **no frontend code change needed**.

---

## Acceptance criteria

1. `sp docker create` → instance is tagged with `sg-compute:host-api-key`.
2. `GET /api/nodes` response includes `host_api_key` (non-empty) for that node.
3. Dashboard boot-log panel shows log lines (not 401) for CLI-launched node.
4. Pods tab shows pod list (not 401) for CLI-launched node.
5. Quick-commands panel executes a command (not "Authentication failed") for CLI-launched node.
6. CI snapshot test for `Schema__Node__Info` verifies the new field exists.

---

## Related bugs

- Bug 1: Boot log 401 (unblocked by this fix)
- Bug 5: Quick-commands auth (unblocked by this fix)
- `BUG-BATCH-1__sidecar-auth-and-terminal.md` — full analysis doc
