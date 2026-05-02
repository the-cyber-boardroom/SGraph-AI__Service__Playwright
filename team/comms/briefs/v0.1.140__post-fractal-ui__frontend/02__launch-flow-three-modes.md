# 02 — Launch flow: three creation modes

## Goal

Extend the launch panel to support the three creation modes (FRESH / BAKE_AMI / FROM_AMI) and the AMI selector, instance size, and timeout fields the 05/01 ephemeral-infra brief enumerates. Today the panel sends `{ stack_name }` only; this is the entry point for ephemeral-infra features 2-10 and must land before any of them.

## Today

- Active launch component: `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launch-panel/v0/v0.1/v0.1.0/sp-cli-launch-panel.{js,html,css}`. Renders inside a sg-layout tab (no longer modal).
- The form is rendered by `_shared/sp-cli-launch-form/...`. Fields today: stack name only. Verify with `sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-launch-form/v0/v0.1/v0.1.0/sp-cli-launch-form.html`.
- Defaults are read from the settings bus via `getAllDefaults()` (`sp-cli-launch-panel.js:3,34`).
- A deprecated `sp-cli-launch-modal` is still on disk and is removed by `04__cleanup-pass.md`.

## Required output

Extend `sp-cli-launch-form` with a creation-mode selector and the supporting fields. The form is the single entry point for every plugin's launch — keep it generic; per-plugin fields stay inside the per-plugin card or detail.

### Layout sketch

```
┌─ Launch <plugin display name> ───────────────────────┐
│  Stack name        [auto if blank          ]         │
│                                                       │
│  Creation mode     ◯ Fresh   ◯ Bake AMI   ◯ From AMI │
│                                                       │
│  ── shows when 'From AMI' selected ──                 │
│  AMI                [select… ▼]                       │
│                                                       │
│  ── always shown ──                                   │
│  Instance size     [Small ▼]                          │
│  Timeout (mins)    [60       ]                        │
│                                                       │
│  ── per-plugin extras slotted here ──                 │
│  <slot name="plugin-fields" />                        │
│                                                       │
│  [Cancel]                              [Launch]       │
└───────────────────────────────────────────────────────┘
```

### Behaviour

- Fields shown / hidden by `creation_mode`:
  - FRESH → stack-name + size + timeout + plugin extras.
  - BAKE_AMI → stack-name + size + timeout + plugin extras + a "name this AMI" field.
  - FROM_AMI → stack-name + AMI picker + size + timeout + plugin extras.
- Defaults pulled per-plugin from the settings bus (`getDefault(type_id, key)`); the existing pattern.
- AMI picker fetches the AMI list (separate sibling endpoint, to be specified) filtered by the plugin's `type_id`.
- On submit, payload matches `Schema__Stack__Create__Request__Base` from the backend brief.

### Events

- Emit `sp-cli:plugin:{type_id}.launch-requested` (existing) with the new payload shape.
- On success, the controller dispatches `sp-cli:launch.success` (existing) and on a `BAKE_AMI` launch additionally `sp-cli:ami.bake.started` with `{ stack_id, target_ami_name }`.
- Validation errors render inline; cross-field errors (e.g. FROM_AMI with no AMI selected) match the backend's `Request__Validator` rules so the UI never sends an invalid payload.

## Acceptance criteria

- `sp-cli-launch-form` renders the three-mode selector and the conditional AMI picker. CSS-only show/hide via a class on the form root (no extra component).
- A new `sp-cli-ami-picker` widget under `_shared/` (or inlined into the launch form) calls the AMI list endpoint and emits `change` with the selected AMI id.
- The form does not submit unless the cross-field validation passes (mirror of `Request__Validator` rules from the backend brief).
- BAKE_AMI launches surface in `sp-cli-activity-pane` as a separate entry type with progress polling.
- Snapshot / rendering test asserting all three modes render their expected field set.
- Reality doc UI fragment updated.

## Open questions

1. **Where does the AMI list endpoint live?** The backend brief lists this as out-of-scope for the payload contract — we need the answer before this UI ships. Recommendation: a sibling backend brief 02b under the same folder.
2. **"Name this AMI" placement.** Inside the launch form, or only in a follow-up step after the bake completes? Recommendation: inside the launch form, optional with a sensible auto-name.
3. **Per-plugin extras slot.** Today plugins do not pass extra fields at launch; the firefox brief implies "load profile" / "MITM script" want to be selectable at launch. Recommendation: `<slot name="plugin-fields" />` in the form, plugin opts in by registering a child custom element. Confirm at review.
4. **`instance_size` mapping visibility.** Show T-shirt sizes only, or show "Small (t3.medium, 2 vCPU, 4 GB)"? Recommendation: T-shirt with hover tooltip.

## Out of scope

- AMI manager UI (list / delete / set default). Sibling brief.
- Sidecar attachment. Sibling brief (container-runtime).
- Multi-instance "stack" launches. Brief 8 in ephemeral-infra; sibling.

## Paired-with

- Backend contract: `../v0.1.140__post-fractal-ui__backend/02__stack-creation-payload-modes.md`.
- Source: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__ephemeral-infra-next-phase.md`.
- Blocked by: backend item 02 must land first.
