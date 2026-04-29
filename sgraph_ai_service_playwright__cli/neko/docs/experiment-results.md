# Neko experiment results

**Status:** TEMPLATE — not yet filled in

Fill this in during `v0.23.x__neko-evaluation`. Run each task 3 times on both Neko and VNC under the controlled environment described in `04__neko-experiment.md`.

## Environment

| Field | Value |
|-------|-------|
| Date | |
| Operator location | |
| Operator connection | |
| Ping to EC2 public IP | |
| Instance type | t3.large, eu-west-2 |
| Neko version | |
| VNC stack version | |

## Results table

| Measurement | VNC median | Neko median | Winner |
|-------------|-----------|------------|--------|
| T4 keystroke latency (ms) | | | |
| T1+T3 frame rate (fps) | | | |
| T1 AJAX update latency (ms) | | | |
| T2 click-to-action latency (ms) | | | |
| T6 reconnect after blip (s) | | | |
| Bandwidth at idle (KB/s) | | | |
| CPU on instance (%) | | | |
| T5 multi-viewer | pass/fail/degraded | pass/fail/degraded | |
| T7 iframe embed | pass/fail | pass/fail | |
| Audio support | yes/no | yes/no | |
| Clipboard sync | yes/no | yes/no | |
| File upload | yes/no | yes/no | |

## Go/no-go evaluation

| Criterion | Threshold | Neko result | Pass? |
|-----------|-----------|-------------|-------|
| T4 keystroke latency | ≤ 80ms median | | |
| T1+T3 frame rate | ≥ 25 fps median | | |
| T7 iframe embed | works or replaceable ≤50% code | | |
| T6 reconnect | ≤ 5s to interactive | | |
| Audio support | present | | |
| T2/T5 vs VNC | no regression | | |

## Recommendation

<!-- adopt / reject / conditional-adopt with rationale -->

## Notes

<!-- Observations, anomalies, anything that surprised you -->
