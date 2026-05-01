# T1 — Kibana Discover: 24h query + scroll

**What it measures:** Text rendering quality, scroll responsiveness, AJAX update latency.

**Scenario:** Open Kibana from a running Elastic stack. Navigate to Discover. Set the time range to last 24h. Run a query against an index with ~10k records. Scroll the result table top-to-bottom three times.

**Measurements to record:**
- Time from clicking "Refresh" to results loading (ms, 3 runs)
- Subjective scroll smoothness: smooth / stuttery / unusable
- Any rendering artefacts (garbled text, missing glyphs)

**Pass threshold:** Results load in < 5s; scroll is smooth on both platforms.
