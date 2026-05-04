# FV2.4 — Specs view (left-nav item + browse pane)

## Goal

Add a "Specs" left-nav item and a `<sp-cli-specs-view>` web component that lets the operator browse the catalogue: per-spec card with manifest, capability chips, version, "Launch a node" button, "Spec detail" tab.

This is a NEW view (not a rename). It surfaces the catalogue-driven information that FV2.3 made available.

## Tasks

1. **Create `<sp-cli-specs-view>`** at `components/sp-cli/sp-cli-specs-view/v0/v0.1/v0.1.0/`. Three-file pattern.
2. **Renders a grid (or list)** of `getCatalogue().specs`. Per spec card shows:
   - Icon (manifest `icon` field).
   - Display name + spec_id (kebab).
   - Stability badge (`STABLE / EXPERIMENTAL / DEPRECATED`).
   - Capability chips (e.g. `vault-writes`, `mitm-proxy`).
   - Version (from `manifest.version`).
   - Boot time estimate.
   - "Launch node" primary button → opens the launch flow with `spec_id` pre-filled (FV2.5 supplies the launch flow).
   - "View detail" link → opens a `<sp-cli-spec-detail>` tab.
3. **Per-spec detail** (`<sp-cli-spec-detail>` — separate component, lighter):
   - Full manifest as a structured panel.
   - The `extends` lineage (visualised as a small DAG; for now all specs have `extends=[]`, so a placeholder).
   - List of AMIs baked from this spec (placeholder until backend ships `/api/amis/<spec_id>`).
   - Link to the spec's README (mounted at `/api/specs/{id}/readme`; backend may need to add this — flag in PR if not present).
4. **Add to left nav** (`sp-cli-left-nav`) — new item `data-view="specs"` between "Compute" and "Settings".
5. **Wire `sp-cli:nav.selected`** listener to mount `<sp-cli-specs-view>` in the main column.
6. **A11y baseline** — keyboard nav, ARIA labels, WCAG AA contrast on stability badges.
7. Update reality doc / PR description.

## Acceptance criteria

- "Specs" appears in the left nav.
- Clicking it shows a grid of all 12 specs.
- Each spec card is keyboard-navigable.
- Empty state ("No specs installed — install a `*-compute-specs` package") renders when the catalogue is empty.
- Stability badges and capability chips render correctly.
- "Launch node" button opens the launch flow (or a stub if FV2.5 hasn't shipped).
- Snapshot tests for the grid + detail.

## Open questions

- **Spec `README` endpoint.** Does backend serve `GET /api/specs/{id}/readme`? If not, omit the link in this phase and flag as follow-up.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** FV2.3 (catalogue loader).

## Notes

The card visual is the **template for FV2.6's catalogue-driven card rendering**. Design decisions made here propagate.
