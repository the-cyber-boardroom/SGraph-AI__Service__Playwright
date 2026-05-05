# T3.5 — Pin to one field-name shape (drop the `||` fallbacks)

⚠ **Tier 3 — integration cleanup.** Standalone PR.

## What's wrong

`admin.js` reads `stack.node_id || stack.stack_name` and `stack.spec_id || stack.type_id` at **6+ sites**. This was added during the FV2.2 migration as a transitional safety net — but it **encodes migration ambiguity** instead of pinning to one shape, and it silently hides regressions where the new field doesn't ship.

Same pattern in `_renderContainers` (sg-compute-nodes-view): `c.pod_name || c.name`, `c.state || c.status` (frontend-late review).

## Why it matters

- Every consumer site that writes `a || b` is a place where a backend regression goes silent.
- The migration is "done"; the fallbacks should die.

## Tasks

1. **Sweep `sgraph_ai_service_playwright__api_site/`** — `grep -rn "stack_name\|type_id\|container_count" --include="*.js"` — list every site.
2. **For each site**, drop the legacy half of the `||`:
   - `stack.node_id || stack.stack_name` → `stack.node_id`.
   - `stack.spec_id || stack.type_id` → `stack.spec_id`.
   - `c.pod_name || c.name` → `c.pod_name`.
   - `c.state || c.status` → `c.state`.
3. **Run the dashboard** — verify nothing breaks (the new fields should be present in every backend response by now).
4. **If a regression appears** (a backend response that doesn't carry the new field): **STOP**. File a backend ticket; don't put the fallback back. The fix is in the backend.

## Acceptance criteria

- `grep -rn "stack_name\|type_id\|container_count" sgraph_ai_service_playwright__api_site/` returns zero hits in active code (or only intentional comments).
- Dashboard works end-to-end — every list, every detail, every launch.
- Console clean.

## "Stop and surface" check

If you find a backend response that still uses the legacy field name: **STOP**. The migration was supposed to be complete. File a backend ticket and ship this PR PARTIAL — list each backend response that needs updating.

## Live smoke test

Exercise every dashboard view: Compute, Specs, Nodes (every tab), Settings, API Docs. No console errors. Nodes list, spec catalogue, pod list all populated correctly.

## Source

Executive review Tier-3; frontend-early review §"Field-name fallbacks".
