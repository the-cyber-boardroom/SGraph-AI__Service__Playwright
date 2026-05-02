# Decisions — Post-Fractal UI Cleanup Pass

**date** 02 May 2026
**session** claude/setup-dev-agent-ui-titBw
**brief** `team/comms/briefs/v0.1.140__post-fractal-ui__frontend/04__cleanup-pass.md`

---

## 4.5 Plugin-folder structure

**Decision:** Ratify the current split.

- `plugins/{name}/v0/v0.1/v0.1.0/` holds the launcher card (`sp-cli-{name}-card.{js,html,css}`)
- `components/sp-cli/sp-cli-{name}-detail/v0/v0.1/v0.1.0/` holds the detail panel (`sp-cli-{name}-detail.{js,html,css}`)

The 04/29 brief suggested collapsing both into `plugins/{name}/`, but the implemented split is functionally equivalent and avoids adding a layout nesting level. Cards are loaded unconditionally (launcher pane iterates them all); details are loaded lazily when a stack is selected. Keeping them in separate directories makes that distinction visible on disk.

No code change needed. This note records the divergence from the brief as accepted.

---

## 5.1 Out-of-brief plugin: `firefox`

**Recommendation:** Ratify. See `05__governance-decisions.md` for context. Firefox shipped via `c5566d2` + `092f069` and the 05/01 firefox brief. The reality doc UI fragment should be updated to list eight plugins once the next Librarian pass runs.

## 5.2 Out-of-brief navigation: `api` view

**Recommendation:** Ratify. The fifth nav item (`api`) was added in `c5566d2`. Having the Swagger docs one click away from the dashboard is operationally useful. Update the 04/29 brief or supersede with a reality-doc note.
