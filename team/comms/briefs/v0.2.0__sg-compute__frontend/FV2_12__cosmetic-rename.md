# FV2.12 — Cosmetic `sp-cli-*` → `sg-compute-*` web-component prefix rename

## Goal

The dashboard has 30+ web components named `sp-cli-{kebab}` ("sp-cli" = SGraph Playwright CLI). Under the v0.2 brand they should be `sg-compute-{kebab}`. This is a sweep across every component file, every `customElements.define()`, every HTML reference, every CSS host selector.

**Un-deferred 2026-05-05 (Architect decision).** Originally deferred to v0.3, but FV2.6 (per-spec UI co-location) requires FV2.12 to run first so co-located files land with their final `sg-compute-*` names. The new API surface is stable (FV2.2–FV2.9 shipped), so the precondition is met.

## Tasks

1. **For every component directory** under `components/sp-cli/sp-cli-{name}/`:
   - `git mv sp-cli-{name} sg-compute-{name}`.
   - Inside the `.js` file:
     - `class SpCli{Name} extends ...` → `class SgCompute{Name} extends ...`
     - `customElements.define('sp-cli-{name}', ...)` → `customElements.define('sg-compute-{name}', ...)`
   - Inside the `.html` file: any reference to a sibling component tag.
   - Inside the `.css` file: any `:host(sp-cli-{name})` selector + any `sp-cli-{name}` selector.
2. **Update every `<script type="module">`** in `admin/index.html` and `user/index.html`.
3. **Update every `document.createElement('sp-cli-{name}-...')` and `document.querySelector('sp-cli-...')`**.
4. **Update test snapshots** (file paths + tag names).
5. **`_shared/sg-remote-browser` family** — already uses `sg-` prefix; stays as-is.
6. **Per-spec UI** — if FV2.6 has migrated some specs' UI to `sg_compute_specs/<name>/ui/`, sweep those too.
7. **Update reality doc / PR description.**

## Strategy

Automate as much as possible:

```bash
# Rename files
find components/sp-cli -maxdepth 1 -type d -name "sp-cli-*" -exec sh -c '
  newname=$(echo "$1" | sed "s|sp-cli-|sg-compute-|")
  git mv "$1" "$newname"
' _ {} \;

# Replace class names + tag names + CSS selectors
find sgraph_ai_service_playwright__api_site -type f \( -name "*.js" -o -name "*.html" -o -name "*.css" \) \
  -exec sed -i 's/sp-cli-/sg-compute-/g; s/SpCli/SgCompute/g' {} +
```

Then **manually verify** by running the dashboard. Snapshot tests catch most regressions; smoke-test every view.

## Acceptance criteria

- `grep -rn "sp-cli-" sgraph_ai_service_playwright__api_site/` returns zero results (or only test-data that's intentionally legacy).
- Every snapshot test passes.
- Manual smoke test of every view + every interaction.
- Reality doc updated.

## Open questions

None — mechanical sweep.

## Blocks / Blocked by

- **Blocks:** FV2.6 (per-spec UI co-location — files must land with final names) + FV2.13 (dashboard move).
- **Blocked by:** FV2.9 (event vocabulary — DONE ✅). All preconditions met.

## Notes

This is **mechanical**. Don't try to be clever — sweep, verify, ship. Snapshot tests are your safety net.
