# Neko plugin — overview

**Status:** STUB — `enabled=False`, pending experiment results

Neko (n.eko) is a self-hosted browser-over-WebRTC alternative to the current VNC + noVNC stack. It offers lower keystroke latency, native audio, and a WebRTC transport that reconnects cleanly after network blips.

This plugin folder was created in `v0.22.19__backend-plugin-architecture` to:

1. Validate that the plugin architecture works for a brand-new compute type.
2. Provide scaffolding for the structured evaluation experiment.

**Nothing here is production-ready.** Every service method raises `NotImplementedError`. The routes return 501. The manifest ships with `enabled=False`.

## Experiment plan

Full task descriptions, measurements, go/no-go criteria:

→ `team/humans/dinis_cruz/briefs/04/29/v0.22.19__backend-plugin-architecture/04__neko-experiment.md`

Short version of tasks:

| ID | What it measures |
|----|-----------------|
| T1 | Kibana Discover — text rendering, scroll, AJAX latency |
| T2 | mitmweb live traffic — rapid DOM updates, click latency |
| T3 | Kibana dashboard 6-viz pan/zoom — frame rate stress |
| T4 | 200-char KQL typing — keystroke-to-display latency |
| T5 | Two simultaneous operator connections — multi-viewer |
| T6 | Network blip (drop 3s) — reconnect time |
| T7 | Iframe embed in admin dashboard — UI integration |

Results template: `docs/experiment-results.md`

## Enabling for experiment

Enabling Neko requires a code change (`enabled=True` in `Plugin__Manifest__Neko`) plus a full Neko implementation in `Neko__Service`. There is no env-var path to enable a manifest-disabled plugin — the env override only disables stable plugins without a redeploy.

## What ships after the experiment

If Neko is adopted (see go/no-go criteria in the experiment plan):

- `v0.23.x__neko-evaluation` brief: real `Neko__Service`, EC2 user-data for Neko Docker, iframe integration, `<sp-cli-neko-viewer>` web component.
- Gradual deprecation of VNC (or coexistence — depends on T5 + T7 results).
