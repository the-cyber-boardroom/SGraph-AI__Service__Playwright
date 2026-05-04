# 04 — Neko Experiment Plan

**Status:** PROPOSED
**Read after:** `01__plugin-registry-design.md`
**Outputs:** A results document that drives the Neko-vs-VNC decision.

---

## What this doc gives you

A **structured experiment** for evaluating Neko (n.eko, self-hosted browser via WebRTC) against the existing VNC + noVNC stack. Specific measurements, specific reference tasks, specific go/no-go criteria. The implementing session does **not** decide whether to adopt Neko — they run the experiment and fill in the results table. The decision happens in a follow-up review based on the results.

This brief delivers the **scaffolding** (plugin manifest, stub service, experiment harness) — not a working Neko deployment.

## Why a structured experiment

The frontend brief and the backend memo both say "Neko if it's good enough; VNC as fallback." That phrasing leaves the implementing session to decide what "good enough" means. The cost of getting that wrong is months of integration work on a tech that turns out to underperform on the actual workloads.

Structured experiments avoid that. We pick **specific reference tasks** that match how operators actually use the remote browser, **specific measurements** taken under controlled conditions, and **specific thresholds** that determine the decision. The implementing session runs it and reports.

## Reference tasks

These are workloads the operator-facing UI actually drives. Each is a recorded scenario the experiment runs against both Neko and VNC.

| ID | Task | Why it matters |
|---|---|---|
| **T1** | Open Kibana from Elastic stack, navigate to Discover, run a 24h time-range query against an index with ~10k records, scroll the result table | Most common operator task. Tests text rendering, scroll responsiveness, AJAX update latency |
| **T2** | Open mitmweb from VNC stack, observe live traffic from a Playwright session, click into a flow, view request/response headers | Real-time streaming UI. Tests rapid DOM updates and click latency |
| **T3** | Open a Kibana dashboard with 6 visualisations, pan/zoom the time picker, watch all 6 viz refresh | Stress test for frame rate and concurrent updates |
| **T4** | Type a 200-character query into a Kibana KQL field at typical typing speed (5 chars/sec) | Keystroke-to-display latency — the most-felt UX measure |
| **T5** | Two operators connect to the same instance simultaneously, both interact with the UI | Multi-viewer / collaborative browsing capability |
| **T6** | Connect to the instance after a network blip (drop wifi 3s, reconnect) | Resilience to network instability |
| **T7** | Embed the remote browser in an iframe inside the admin dashboard. Verify the existing `<sp-cli-vnc-viewer>` pattern works for both | UI integration — does it fit our existing pane layout? |

## Measurements

Each task is run **3 times per platform** (Neko and VNC). Results recorded in a table.

| Measurement | Unit | How measured |
|---|---|---|
| **Keystroke-to-display latency** | ms | Stopwatch via screen recording: time from keypress to glyph appearing on remote screen. T4 |
| **Click-to-action latency** | ms | Time from mouse click to visual confirmation of action (button press animation, dropdown open). T2, T3 |
| **Frame rate during pan/zoom** | fps | Screen capture analysis (e.g. `ffmpeg`-derived) during T3 |
| **Bandwidth utilisation** | KB/s | Network monitor on operator side, sustained during T1 + T3 |
| **CPU load on instance** | % | Read from `/proc/stat` over the test window |
| **Concurrent-viewer behaviour** | functional | T5 — pass/fail/degraded. Note the UX: do both see the same screen? Can both move the cursor? |
| **Reconnect time after blip** | seconds | T6 — wall-clock from network restored to interactive again |
| **Iframe embedding** | functional | T7 — pass/fail. Note any X-Frame-Options or CSP issues |
| **Audio support** | functional | Try playing a video in the remote browser. Does audio reach the operator? |
| **Clipboard sync** | functional | Copy text in remote browser, paste locally — does it work? |
| **File upload** | functional | Drag a file onto the remote browser — does it transfer? |

## Test environment (controlled)

- **Operator side**: laptop in EU (London), wired ethernet, Chrome stable, 1080p display, 16GB RAM, recent CPU
- **Instance side**: t3.large in `eu-west-2`, single AZ, Linux 2023, Docker installed
- **Network path**: public internet from operator → CloudFront → Lambda (irrelevant for streaming) → direct EC2 public IP via SG ingress
- **Network conditions**: report ping to the public IP from the operator at the start of each session

## Go/no-go criteria

Neko adoption is **recommended** if all of these are true:

1. **T4 keystroke latency**: median ≤ 80ms (current VNC measured around 110-150ms in informal testing — Neko should beat this for adoption to be worthwhile)
2. **T1 + T3 frame rate**: ≥ 25 fps median during interactive use
3. **T7 iframe embedding**: works without breaking the existing `<sp-cli-vnc-viewer>` 5-state pattern, OR is replaceable by a parallel `<sp-cli-neko-viewer>` with no more than ~50% more code
4. **T6 reconnect**: ≤ 5 seconds to interactive
5. **Audio support**: present (Neko-specific advantage worth claiming)
6. **No regression** on T2 / T5 vs current VNC

Neko is **rejected** if any of:

1. T4 keystroke latency median > 150ms (worse than VNC)
2. T7 cannot embed in iframe — would require a parallel UI flow incompatible with the rest of the admin dashboard
3. Multi-viewer (T5) breaks in a way that surprises operators (e.g., both cursors visible but only one functional, no warning)
4. Bandwidth at idle > 1 MB/s (would make it unsuitable for operators on poor connections)

Neko is **conditional adoption** (e.g., "use it for these workloads, keep VNC for these") if results are mixed — that's a real possible outcome and the doc should leave room for it.

## What ships in this brief — the scaffolding

```
sgraph_ai_service_playwright__cli/neko/
├── plugin/
│   ├── Plugin__Manifest__Neko.py         enabled=False, stability=experimental
│   └── __init__.py
├── service/
│   ├── Neko__Service.py                  raises NotImplementedError on every method
│   └── __init__.py
├── fast_api/
│   └── routes/
│       └── Routes__Neko__Stack.py        empty router; routes return 501 Not Implemented
├── schemas/
│   └── Schema__Neko__Stack__Info.py      stub; copy structure from Schema__Vnc__Stack__Info
└── docs/
    ├── README.md                         points to this brief
    ├── experiment-results.md             template — implementing session of the *experiment* fills this in (not this brief)
    └── tasks/
        ├── T1__kibana-discover.md        recorded scenario per task
        ├── T2__mitmweb-flows.md
        ├── T3__kibana-dashboard.md
        ├── T4__kql-typing.md
        ├── T5__multi-viewer.md
        ├── T6__network-blip.md
        └── T7__iframe-embed.md
```

The Neko **service** stub:

```python
class Neko__Service(Type_Safe):
    """Stub. Plugin loaded with enabled=False until experiment completes."""

    def setup(self):
        pass

    def create_stack(self, *args, **kwargs):
        raise NotImplementedError(
            'Neko plugin is enabled=False. See team/comms/briefs/v0.22.19__'
            'backend-plugin-architecture/04__neko-experiment.md for the '
            'evaluation plan that gates this implementation.')

    def list_stacks(self, *args, **kwargs):
        return []
    
    def delete_stack(self, *args, **kwargs):
        raise NotImplementedError('see Plugin__Manifest__Neko docstring')
```

Tests for Neko in this brief:

- `test__plugin__manifest_loads_with_enabled_false` — registry skips it
- `test__plugin__manifest_loads_with_enabled_true__service_calls_raise` — when manually enabled, the routes mount but every operation NotImplementedError-s
- `test__catalog__entry_present_with_available_false` — the catalog shows the SOON tile shape

That's it. The actual Neko Docker image, the EC2 user-data, the iframe wiring, the WebRTC client integration — none of those ship in this brief.

## What the experiment brief (later) will deliver

A new brief, distinct from this one, that does:

1. Build the Neko AMI (or Docker image deployable on Linux AMI). 
2. Implement `Neko__Service.create_stack()` etc. — full provisioning.
3. Run the 7 tasks, record results in `experiment-results.md`.
4. Recommend adopt / reject / conditional-adopt with rationale.
5. If adopt: a follow-up brief for moving the default remote browser from VNC to Neko in the UI, deprecating VNC over a release, etc.

Suggested label: **`v0.23.x__neko-evaluation`** or similar.

## Why this matters for the brief's structure

The experiment doc is the **forcing function** that makes the plugin model worthwhile. Without it, "we have plugins but every plugin works the same as before" is a structural change with little practical payoff. With it: the *first new plugin* is something we genuinely don't know if we want, and the plugin shape lets us answer that question without mortgaging the existing system.

If the experiment says "reject Neko," we ship the structural change anyway and learn from the experience. If it says "adopt," we have a faster, better remote-browser stack with no rebuild of the platform shell. **Either result validates the architecture.**
