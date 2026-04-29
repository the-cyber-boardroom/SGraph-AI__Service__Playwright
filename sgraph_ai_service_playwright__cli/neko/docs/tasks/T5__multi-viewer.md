# T5 — Multi-viewer: two simultaneous operator connections

**What it measures:** Whether collaborative browsing works and what the UX is for shared cursor/control.

**Scenario:** Two operators (different machines or browser tabs) connect to the same instance. Both interact with the UI: operator A opens a page, operator B scrolls. Swap: operator B types into a field, operator A watches. Note the behaviour.

**Measurements to record:**
- Does the second connection succeed at all?
- Can both operators see the same screen in real time?
- What happens to cursor control — exclusive to one? Shared? Fighting?
- Does performance degrade for either operator when both are connected?
- Any error messages or disconnections?

**VNC baseline:** noVNC allows multiple simultaneous connections, shared screen, shared cursor (last move wins). No auth separation.

**Pass threshold:** Both operators see the same screen; UX is predictable (even if not ideal — surprising behaviour is a rejection signal).
