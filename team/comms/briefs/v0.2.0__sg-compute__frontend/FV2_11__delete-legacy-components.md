# FV2.11 — Delete legacy components + external call

## Goal

Code review flagged dead code and a privacy concern:

- `sp-cli-stacks-pane` — legacy active-nodes list, superseded by `sp-cli-nodes-view`. Frontend audit confirmed deletable after FV2.4 / FV2.6 stabilise.
- `shared/catalog.js` — old catalog cache, superseded by `shared/spec-catalogue.js` (FV2.3).
- `sp-cli-launch-form` calls `api.ipify.org` — third-party privacy/supply-chain concern. Replace with backend-side IP detection or local fallback.

This phase cleans these up.

## Tasks

1. **Verify nothing depends on `sp-cli-stacks-pane`.** Search for `<sp-cli-stacks-pane>` usage:
   ```
   grep -rn "sp-cli-stacks-pane" sgraph_ai_service_playwright__api_site/
   ```
   Should be near-zero (only the component's own folder + maybe a comment).
2. **Delete `components/sp-cli/sp-cli-stacks-pane/`**. Update any leftover script tags in `admin/index.html`.
3. **Verify `shared/catalog.js`** is unused — `grep -rn "shared/catalog" sgraph_ai_service_playwright__api_site/` should be near-zero. Delete the file.
4. **Replace `api.ipify.org` call** in `sp-cli-launch-form.js`:
   - Option A (preferred): backend SP CLI `/catalog/caller-ip` endpoint that detects the caller's IP server-side. Works for any client; no third-party dependency. Backend may need to add this — flag for backend backlog if not present.
   - Option B (fallback): use a local heuristic — if the dashboard origin includes `localhost`, use `127.0.0.1`; otherwise prompt the operator for their IP.
   - Either way: no third-party calls from the dashboard.
5. **Sweep for any other third-party calls** in the dashboard. There should be none (per the no-build / native-modules constraint, but verify).
6. Update reality doc / PR description.

## Acceptance criteria

- `components/sp-cli/sp-cli-stacks-pane/` does not exist.
- `shared/catalog.js` does not exist.
- No call to `api.ipify.org` (or any other third-party origin) from the dashboard.
- Smoke test passes — launch form still detects caller IP.
- Snapshot tests updated.

## Open questions

- **Backend `/catalog/caller-ip` endpoint** — does it exist? If not, file backend ticket and use Option B in the meantime.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** FV2.3 (catalogue loader; otherwise `shared/catalog.js` may still be in use), FV2.4 (Specs view; replaces `sp-cli-stacks-pane` overlap).

## Notes

This is **dead-code cleanup**. After it lands, the dashboard tree is leaner and the security surface is smaller (no third-party fetch).
