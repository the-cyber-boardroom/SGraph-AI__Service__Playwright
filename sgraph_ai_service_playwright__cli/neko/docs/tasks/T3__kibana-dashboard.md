# T3 — Kibana dashboard: 6-viz pan/zoom stress test

**What it measures:** Frame rate and concurrent-update handling under visual stress.

**Scenario:** Open a Kibana dashboard with 6 visualisations. Pan the time picker left and right 5 times, watching all 6 vizualisations refresh each time. Zoom in to a 1h window then back out to 7d.

**Measurements to record:**
- Frame rate during active pan/zoom (fps) — measure via screen recording: `ffmpeg -i recording.mp4 -vf fps=1 ... ` or subjective estimation
- Time for all 6 viz to finish refreshing after each time-picker change (ms)
- Any viz that fails to refresh or displays stale data

**Pass threshold:** ≥ 25 fps sustained; all 6 viz refresh within 8s of time-picker change.
