# Backend follow-up — GET /api/amis list endpoint

**Filed by:** Frontend team (T2.1 implementation)
**Date:** 2026-05-05
**Priority:** Tier 2 — required to complete T2.1 AMI picker (currently PARTIAL)

---

## Why this is needed

T2.1 ships `<sg-compute-ami-picker>` — a component that will display a dropdown of AMIs for a given spec so users can choose a pre-baked image when launching in FROM_AMI mode. The component is complete but cannot populate without this endpoint. It currently shows a placeholder warning.

## Required endpoint

```
GET /api/amis?spec_id=<id>
```

### Response shape (proposed)

```json
{
  "amis": [
    {
      "ami_id": "ami-0abcdef1234567890",
      "name": "docker-base-20260505",
      "created_at": "2026-05-05T10:00:00Z",
      "state": "available",
      "size_gb": 8
    }
  ]
}
```

### Behaviour

- Filter by `spec_id` — only return AMIs tagged for that spec (e.g. `sg-compute-spec = docker`).
- Empty `amis: []` is valid — the picker shows "No AMIs for this spec — try Fresh or Bake AMI mode."
- Only return `state = available` AMIs.
- Order newest-first.

## Frontend integration point

`sg-compute-ami-picker.setSpecId(specId)` is the hook. Once the endpoint exists, implement the fetch there:

```js
setSpecId(specId) {
    this._specId = specId
    fetch(`/api/amis?spec_id=${encodeURIComponent(specId)}`, { headers: ... })
        .then(r => r.json())
        .then(data => this._populateAmis(data.amis || []))
}
```

The placeholder `<div class="ami-placeholder">` should be hidden once the fetch completes (success or empty).

## Follow-up required

When this backend route is shipped, update:
1. `sg-compute-ami-picker.js` — implement `setSpecId()` fetch + `_populateAmis()`
2. The T2.1 debrief — change PARTIAL status to COMPLETE
3. Reality doc — mark AMI picker as fully operational
