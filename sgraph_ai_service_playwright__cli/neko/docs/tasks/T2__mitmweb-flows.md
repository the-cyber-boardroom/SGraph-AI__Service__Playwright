# T2 — mitmweb: live traffic observation + flow inspection

**What it measures:** Rapid DOM update handling; click-to-action latency on a streaming UI.

**Scenario:** Open mitmweb from a running VNC stack while a Playwright session generates traffic. In the mitmweb UI observe at least 20 flows appearing in real time. Click into 5 flows. View request and response headers on each. Navigate back to the list.

**Measurements to record:**
- Click-to-action latency: time from clicking a flow row to the detail panel opening (ms, 5 runs)
- Does live flow list update smoothly or freeze/stutter?
- Any missed clicks (click registered in browser but no action in mitmweb)?

**Pass threshold:** Click latency < 300ms median; live updates visible with no > 1s freeze.
