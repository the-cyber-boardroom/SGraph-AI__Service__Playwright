# FV2.5 — Launch flow with three creation modes + AMI/size/timeout

## Goal

The original v0.1.140 post-fractal-UI brief item 02 called for the launch form to support three creation modes (FRESH / BAKE_AMI / FROM_AMI) plus AMI selector + instance size + timeout fields. Backend `Schema__Stack__Create__Request__Base` was supposed to carry these. Status today (per audit): **not built** — the launch form sends only `stack_name`.

This phase delivers the launch flow once BV2.5 ships `POST /api/nodes` + `EC2__Platform.create_node`.

## Tasks

1. **Extend `<sp-cli-launch-form>`** at `components/sp-cli/_shared/sp-cli-launch-form/`:
   - **Creation mode** (radio or segmented control): FRESH / BAKE_AMI / FROM_AMI.
   - Conditional reveal:
     - FRESH → stack-name + size + timeout + plugin extras.
     - BAKE_AMI → stack-name + size + timeout + plugin extras + "name this AMI" field.
     - FROM_AMI → stack-name + AMI picker + size + timeout + plugin extras.
   - Defaults pulled per-spec from the manifest (`boot_seconds_typical`, etc.).
   - Submit payload matches `Schema__Stack__Create__Request__Base`.
2. **Build `<sp-cli-ami-picker>`** (under `_shared/`) — dropdown of AMIs for a given spec. Empty state ("No AMIs for this spec — try Fresh or Bake AMI mode"). Endpoint: `GET /api/amis?spec_id=<id>` (backend may need to add — flag if not present).
3. **Validation** — FROM_AMI without an AMI selected = disabled submit.
4. **BAKE_AMI cost preview** — surface estimated time (~10 min) + warning ("storage cost ~$0.05/GB/month"). Visual: an info banner on the form.
5. **Events** — emit `sp-cli:plugin:{spec_id}.launch-requested` (existing) with the new payload shape. On success: `sp-cli:node.launched` + (when BAKE_AMI) `sp-cli:ami.bake.started`.
6. **A11y** — keyboard nav for the mode selector; ARIA on AMI picker; focus-visible.
7. Update reality doc / PR description.

## Acceptance criteria

- Form renders the three-mode selector + conditional AMI picker + size/timeout fields.
- Mode switch hides/shows fields without page reload.
- Submit blocked until valid (mirrors backend `Request__Validator`).
- BAKE_AMI launches surface in `sp-cli-activity-pane` (or events log) as a separate entry.
- Snapshot tests for all three modes.

## Open questions

- **AMI list endpoint.** Backend brief implied a sibling endpoint; v0.2 backend phases don't explicitly add it. **Flag for BV2.x backlog: `GET /api/amis?spec_id=<id>`.**
- **Cost preview accuracy.** v0.2.x can ship a static estimate; v0.3 may want a live-pulled estimate from AWS. Architect call.

## Blocks / Blocked by

- **Blocks:** none direct.
- **Blocked by:** BV2.5 (`POST /api/nodes` + `EC2__Platform.create_node`). Without it, FROM_AMI / BAKE_AMI can't actually launch.

## Notes

Per-spec extras (e.g. firefox "Load Profile" field) slot into the form via `<slot name="plugin-fields" />`. Per-spec card components add their own custom-element children.
