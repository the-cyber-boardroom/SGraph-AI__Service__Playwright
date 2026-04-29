# T6 — Network blip: reconnect after 3-second drop

**What it measures:** Resilience to the network instability operators realistically encounter (wifi hiccup, VPN reconnect, hotel wifi).

**Scenario:** While connected and actively viewing the remote browser, drop the network for exactly 3 seconds (disable wifi adapter, re-enable). Measure from network-restored to interactive-again (able to click something in the remote browser and see a response).

**Measurements to record:**
- Reconnect time: seconds from network-restored to interactive. Record 3 runs.
- Does the browser show a reconnecting indicator or just a frozen/black screen?
- Is state preserved (same page, same scroll position) after reconnect?
- Any data loss (partial text entry lost, form fields cleared)?

**Pass threshold:** ≤ 5 seconds to interactive. State preservation is a bonus but not a hard requirement.
