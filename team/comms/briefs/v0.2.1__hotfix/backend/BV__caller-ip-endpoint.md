# Backend brief — GET /catalog/caller-ip endpoint

**Filed by:** Frontend team (T2.5 implementation)
**Date:** 2026-05-05
**Priority:** Tier 2 — improves caller-IP UX (currently using local heuristic as Option B interim)

---

## Context

FV2.11 deleted the `api.ipify.org` call (third-party, no-dashboard-calls policy). The caller IP was used to restrict the EC2 security group ingress rule to the operator's machine.

T2.5 shipped Option B (local heuristic): `localhost` → `127.0.0.1`; remote → empty field with helper text and a Google "what is my IP" link. This preserves privacy but requires the operator to fill in their IP when deploying to a remote host.

## Required endpoint

```
GET /catalog/caller-ip
```

No parameters. The backend reads `X-Forwarded-For` (set by CloudFront / Lambda Web Adapter) and returns the originating IP.

### Response shape

```json
{ "ip": "203.0.113.42" }
```

- If `X-Forwarded-For` is not set (direct invoke): return `""` or `null`.
- No auth required is fine — this reveals only the caller's own IP to themselves.

## Frontend integration point

`sg-compute-launch-form._seedCallerIp()` is the hook. Once the endpoint exists:

```js
_seedCallerIp() {
    if (!this._callerIpInput) return
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
        this._callerIpInput.value = '127.0.0.1'
        return
    }
    // When backend ships, replace the empty-field fallback with:
    import { apiClient } from '/ui/shared/api-client.js'
    apiClient.get('/catalog/caller-ip').then(r => {
        if (r?.ip && !this._callerIpInput.value) this._callerIpInput.value = r.ip
    }).catch(() => {})
}
```

## Follow-up required

When backend ships:
1. Update `sg-compute-launch-form._seedCallerIp()` to call `GET /catalog/caller-ip`
2. Remove the "Find my public IP" link from the form (no longer needed)
3. Update T2.5 debrief — change PARTIAL to COMPLETE
