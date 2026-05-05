# T1.7 — Fix `/ui/...` absolute imports in co-located spec details

🔴 **Tier 1 — runtime breakage.** Standalone PR.

## What's wrong

FV2.6 co-located spec detail JS files into `sg_compute_specs/<spec>/ui/detail/.../`. The dev wrote the imports as **absolute paths starting with `/ui/`**:

```js
// sg_compute_specs/firefox/ui/detail/.../sg-compute-firefox-detail.js:2-9
import { foo } from '/ui/shared/...'
import { bar } from '/ui/components/...'
```

Before BV2.10, `/ui/` happened to be served at the dashboard root by the legacy `Fast_API__SP__CLI` static mount. After BV2.10 folded SP-CLI under `/legacy/`, **`Fast_API__Compute` no longer mounts `/ui/` at root**. ES module resolution will fail; spec detail panels likely throw at load.

The backend BV2.19 added a `StaticFiles` mount but at `/api/specs/<id>/ui/` — not at `/ui/`.

## Why it matters

The dashboard's main user surface is broken in production. No regression test catches it because no test renders the panels in a real browser context.

## Tasks (pick one)

### Option A — relative imports (recommended; frontend-only fix)

1. **Find every `/ui/` import** in `sg_compute_specs/*/ui/detail/.../*.js`:
   ```
   grep -rn "from ['\"]\/ui\/" sg_compute_specs/
   ```
2. **Convert each to a relative path** — from `sg_compute_specs/firefox/ui/detail/.../foo.js`, `/ui/shared/bar.js` becomes `../../shared/bar.js` (verify the actual depth).
3. **Verify the imports resolve** — open the dashboard in a browser; navigate to a spec detail panel; check DevTools Console for module-resolution errors.

### Option B — backend mount at `/ui/` (coordinate with backend)

1. Backend adds an additional `StaticFiles` mount at root path `/ui/` serving the relevant shared assets.
2. Frontend imports stay as-is.
3. Cost: another mount; possible path collision with other routes; harder to reason about.

**Recommend Option A.** Frontend-only; co-location is the new normal; relative imports are the standard pattern.

## Acceptance criteria

- `grep -rn "from ['\"]\/ui\/" sg_compute_specs/` returns zero hits (Option A) OR the backend mount is documented and tested (Option B).
- **Live browser smoke test:** open the dashboard, click each migrated spec's detail tab (firefox, docker, podman, vnc, neko, prometheus, opensearch, elastic). Each renders with no console errors. Take screenshots; attach to PR.
- Spec detail panels' interactive elements (tabs, buttons) work end-to-end.

## "Stop and surface" check

If converting to relative paths breaks something else (e.g. a shared util that's used across plug-ins): **STOP**. The shared util may need to live at a stable URL; surface to Architect — Option B might be the right call after all.

## Live smoke test (acceptance gate)

Open the dashboard in a browser. Click into each migrated spec's detail tab. Open DevTools Console. **Zero red errors.** Click each interactive element in the detail (tabs, buttons, links). All work. Screenshot the Console showing no errors and attach to PR.

## Source

Executive review T1.7; frontend-early review §"Top integration issue (FV2.6)".
