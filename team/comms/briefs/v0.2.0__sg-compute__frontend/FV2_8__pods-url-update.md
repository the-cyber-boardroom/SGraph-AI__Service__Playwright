# FV2.8 — Confirm zero `/containers/*` URL references in dashboard

## Goal

After FV2.7 (Pods tab via unified URL), the dashboard should have no remaining `/containers/*` URL constructions. This phase is the **gate** that confirms it — once green, BV2.17 can delete the sidecar's `/containers/*` aliases.

## Tasks

1. **Sweep for legacy URL constructions:**
   ```
   grep -rn "/containers/" sgraph_ai_service_playwright__api_site/
   ```
   Should return zero hits in active code paths (test data may match — that's fine).
2. **Sweep for the `containers` literal in URL builders:**
   ```
   grep -rn "containers" sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-nodes-view/ | grep -v "Pods\|pods/"
   ```
3. **Update any UI label that says "Container"** referring to a Docker container inside a node — replace with "Pod".
4. **Update field-name consumers** if any component still reads `container_count` from the host status — should be `pod_count` per BV2.6 / FV2.2 reaches.
5. **Browser DevTools verification** — open the dashboard, exercise the Pods tab + Boot Log tab + Overview tab. Network tab shows zero `/containers/*` calls.
6. Update reality doc / PR description.

## Acceptance criteria

- `grep -rn "/containers/" sgraph_ai_service_playwright__api_site/` returns zero hits in active code.
- Pods tab reflects "Pods" label everywhere (no "Container").
- Browser smoke test confirms no `/containers/*` in Network tab.
- Reality doc updated.

## Open questions

None.

## Blocks / Blocked by

- **Blocks:** BV2.17 (sidecar alias deletion). Backend gates BV2.17 on this phase landing.
- **Blocked by:** FV2.7 (unified Pods URL).

## Notes

This is a **verification** phase — small but critical because BV2.17's deletion of the sidecar aliases is irreversible.
