# T3.3 — FV2.12 cosmetic rename leftovers

⚠ **Tier 3 — integration cleanup.** Standalone PR.

## What's wrong

FV2.12 was mechanically thorough on tag names and class names — zero `sp-cli-` residue in `customElements.define()` calls or `class SpCli...` declarations. **But:**

1. **Parent dir `components/sp-cli/` retained** — 38 import paths still read `components/sp-cli/sg-compute-*` (the children renamed; the parent didn't).
2. **`user/index.html` lines 31, 37, 39, 40** reference `sg-compute-launch-modal`, `sg-compute-stack-detail`, `sg-compute-vault-activity` — **these directories don't exist** (deleted in commit `510337d` long ago). The sed-rename happily updated dead script srcs without verification.
3. **Event-vocabulary spec** (`library/docs/specs/v0.2.0__ui-event-vocabulary.md`) still references `sp-cli-stacks-pane.js` (deleted by FV2.11 7 hours earlier).

## Tasks

1. **Rename `components/sp-cli/` → `components/sg-compute/`** with `git mv`. Sweep all 38 import paths.
2. **Delete the dead `<script>` tags** from `user/index.html:31,37,39,40`. Verify the user page still renders.
3. **Sweep for other dead `<script>` tags** — `find sgraph_ai_service_playwright__api_site -name "*.html" | xargs grep -l "<script.*sg-compute-"` and verify each src exists on disk.
4. **Update the event-vocabulary spec** — remove the `sp-cli-stacks-pane.js` reference; replace with the current FAMILIES-map source (`sg-compute-events-log.js`).

## Acceptance criteria

- `grep -rn "components/sp-cli/" sgraph_ai_service_playwright__api_site/` returns zero hits.
- Every `<script src=".../sg-compute-*">` in HTML resolves to an existing file on disk.
- Event-vocabulary spec is current.

## "Stop and surface" check

If renaming the parent dir collides with something elsewhere (e.g. an import from outside the dashboard tree): **STOP** — surface to Architect. The fix may need to coordinate with the eventual FV2.13 dashboard move.

## Live smoke test

Open the dashboard + the user page in a browser. No 404s in the Network tab for `<script>` tags. Console clean.

## Source

Executive review Tier-3; frontend-late review §"Cosmetic rename FV2.12 leftovers".
