# T7 — Iframe embed in admin dashboard

**What it measures:** Whether Neko can slot into the existing `<sp-cli-vnc-viewer>` 5-state panel pattern, or requires a parallel web component.

**Scenario:** Attempt to embed the Neko UI in an `<iframe>` inside the admin dashboard (the same pane that currently hosts `<sp-cli-vnc-viewer>`). Check for X-Frame-Options or CSP headers that block embedding. Test that the iframe is interactive (not sandboxed to a point where WebRTC fails).

**Measurements to record:**
- Does the Neko page serve `X-Frame-Options: DENY/SAMEORIGIN`? (blocks iframe)
- Are there CSP headers that block `frame-src`?
- If embeddable: does WebRTC work inside an iframe? (some browsers restrict getUserMedia in cross-origin iframes)
- Estimated LOC to implement `<sp-cli-neko-viewer>` vs reusing `<sp-cli-vnc-viewer>` with a URL swap

**Pass threshold:** Works in iframe with no X-Frame-Options block; WebRTC functional inside iframe; web component reuse or new component ≤ 50% more code than VNC viewer.

**Rejection trigger:** Cannot embed at all (headers block it and Neko config doesn't expose a way to disable them), AND a parallel full-page viewer would break the admin dashboard layout.
