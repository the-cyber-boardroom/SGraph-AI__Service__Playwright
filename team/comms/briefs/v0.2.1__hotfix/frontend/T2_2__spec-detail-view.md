# T2.2 — Build `<sg-compute-spec-detail>` (FV2.4 silently dropped this)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

FV2.4 brief Task 3 required a per-spec detail tab (`<sp-cli-spec-detail>` / now `<sg-compute-spec-detail>`) that opens when the user clicks a spec card on the Specs view. The detail shows:

- Full manifest as a structured panel.
- The `extends` lineage (visualised — for now all specs are `extends=[]`, so a placeholder).
- List of AMIs baked from this spec (placeholder until backend AMI list endpoint).
- Link to the spec's README (mounted at `/api/specs/{id}/readme`).
- "Launch node" link → opens FV2.5 launch flow with `spec_id` pre-filled.

**None of this shipped.** The Specs view only shows a grid of cards; no detail tab.

## Tasks

1. **Create `components/sp-cli/sg-compute-spec-detail/v0/v0.1/v0.1.0/sg-compute-spec-detail.{js,html,css}`**.
2. **Manifest panel** — render every field from `Schema__Spec__Manifest__Entry`:
   - spec_id, display_name, icon
   - version, stability badge
   - nav_group, capabilities (chips)
   - boot_seconds_typical
   - extends list
   - create_endpoint_path
3. **Extends lineage** — a small DAG visualisation. For now all specs are `extends=[]`, so render "(no parent specs)" as the placeholder.
4. **AMI list** — placeholder section. If `/api/amis?spec_id=<id>` exists, populate; otherwise "AMI list will appear here once the backend `/api/amis` endpoint is wired (T2.x backend backlog)".
5. **README link** — anchor to `/api/specs/{id}/readme`. If the backend doesn't serve this, omit or show a placeholder.
6. **"Launch node" button** — opens the FV2.5 launch flow tab with `spec_id` pre-filled. Coordinate with T3.2 (collapse dual launch flows).
7. **Wire the click on `<sg-compute-specs-view>` cards** — clicking a card opens the detail in a new tab.
8. **Tests** — snapshot test of the detail panel.

## Acceptance criteria

- `<sg-compute-spec-detail>` exists with the canonical three-file pattern.
- Click a spec card on the Specs view → detail tab opens.
- All listed manifest fields render.
- "Launch node" button opens the launch flow with `spec_id` pre-filled.
- Snapshot test covers a representative spec (e.g. firefox).

## "Stop and surface" check

If the backend AMI list endpoint isn't there: **STOP** and file the backend follow-up brief; ship the placeholder section labelled clearly. Don't silently skip the section.

## Live smoke test (acceptance gate)

Open the dashboard. Click "Specs" in the left nav. Click any spec's card. Detail tab opens with full manifest visible. Click "Launch node" → launch flow opens with the spec pre-filled. Screenshot; attach to PR.

## Source

Executive review Tier-2; frontend-early review §"Top contract violation (FV2.4 scope-cut)".
