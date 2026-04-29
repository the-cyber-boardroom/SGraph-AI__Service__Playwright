# T4 — KQL typing: keystroke-to-display latency

**What it measures:** The most-felt UX metric — how long between pressing a key and seeing the glyph appear in the remote browser.

**Scenario:** Open the Kibana KQL search field. Type a 200-character query at a controlled pace of 5 characters per second (use a metronome or counted rhythm). Record the session. Repeat 3 times per platform.

**Measurements to record:**
- Keystroke-to-display latency: time from keypress to glyph appearing in remote screen. Measure from screen recording by stepping frame by frame at the keypress and first visible glyph. Report median of 10 sampled keystrokes per run.
- Any missed keystrokes (typed but not appeared in remote)?
- Any reordering of characters (common in high-latency sessions)?

**Pass threshold (adoption):** Median ≤ 80ms. Above 150ms → rejection criterion.
