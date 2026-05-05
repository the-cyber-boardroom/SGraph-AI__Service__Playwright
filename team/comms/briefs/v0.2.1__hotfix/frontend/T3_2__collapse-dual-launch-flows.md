# T3.2 — Collapse the dual launch flows

⚠ **Tier 3 — integration cleanup.** Standalone PR. **Coordinate with T2.1 (must ship after).**

## What's wrong

Dashboard has TWO launch flows:

- `sg-compute-compute-view._launch()` POSTs `/api/nodes` with `node_name` (the FV2.5 path — the new shape).
- `sg-compute-launch-panel._launch()` POSTs `entry.create_endpoint_path` with **legacy** `stack_name` / `public_ingress` / `caller_ip:''` (`sg-compute-launch-panel.js:48-55,61`).

FV2.4's "Launch node" button on the Specs view emits `sp-cli:catalog-launch` which routes to the **legacy** panel — **bypassing FV2.5 entirely**.

## Why it matters

Two flows = two surfaces to maintain, two places for bugs, contradictory field names (`node_name` vs `stack_name`). The whole point of FV2.5 was a single canonical launch flow.

## Tasks

1. **Deprecate `sg-compute-launch-panel`** as the launch surface. Keep the file as a thin re-export wrapper that opens the FV2.5 form (or delete entirely — confirm no other consumer).
2. **Re-route every "Launch" trigger** to the FV2.5 flow:
   - Spec card "Launch node" button (FV2.4 Specs view).
   - Compute view "Launch" anywhere it appears.
   - Stacks pane "+ New" button (if any).
3. **Remove the `sp-cli:catalog-launch` event** if it's now dead (or list it as DEPRECATED in the events log + spec doc).
4. **Verify** — every launch trigger ends up in `<sg-compute-launch-form>` with the FV2.5 mode selector. Take a screenshot of each entry point.
5. **Sweep field names** — `stack_name` / `public_ingress` / `caller_ip:''` referenced in launch-panel must die with the launch-panel.

## Acceptance criteria

- Only ONE launch surface: `<sg-compute-launch-form>` (FV2.5).
- Every "Launch" trigger routes to it.
- `sg-compute-launch-panel` deleted or shimmed.
- `sp-cli:catalog-launch` deprecated or removed.
- No more legacy field names (`stack_name`, `public_ingress`, `caller_ip:''`) in launch code.

## Blocked by

T2.1 must ship first — the FV2.5 launch flow must support all three modes before we can route everything through it.

## Live smoke test

Click "Launch" from every entry point (Compute view, Specs view card, Stacks pane). Each opens the same FV2.5 form. Submit; backend `POST /api/nodes` is called with `node_name`. Screenshot all entry points + the resulting form.

## Source

Executive review Tier-3; frontend-early review §"Top pattern violation (dual launch flows)".
