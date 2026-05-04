# Next Session Handover — SG/Compute Frontend (F1 / F2 / F5)

**Date:** 2026-05-04
**For:** Next Claude Code session picking up the SG/Compute frontend migration
**Current version:** `v0.1.169` (`sgraph_ai_service_playwright/version`)
**Branch to start from:** `dev` (all session work merged)

---

## 1. Context in one paragraph

The SG/Compute backend migration (B1–B8) is complete. The compute control
plane (`Fast_API__Compute`) serves `GET /api/specs` and `GET /api/nodes` with
new typed schemas. A parallel UI session (this handover's predecessor) built
the **node-detail panel** (`sp-cli-nodes-view`) with Terminal, Shell auth, EC2
Info, Pods, and Host API tabs, and hardened the sidecar with CORS + cookie auth.
What has NOT been done: the main dashboard still loads specs and nodes from the
old `/catalog/types` and `/catalog/stacks` endpoints using old field names
(`stack_name`, `type_id`, `state: 'running'`). That is your job.

---

## 2. Read first (in this order)

1. `team/comms/briefs/v0.1.140__sg-compute__frontend-handover/README.md` — full F1/F2/F5 task list
2. `team/comms/briefs/v0.1.140__sg-compute__frontend-handover/02__sidecar-ui-addendum.md` — what changed in the previous session, corrections to the brief, and the critical F2 risk
3. `team/comms/briefs/v0.1.140__sg-compute__migration/20__frontend-plan.md` — phase-by-phase detail

---

## 3. Your starting state

### What's wired correctly already
- `sp-cli-nodes-view` renders a full node-detail panel (6 tabs)
- CORS is fixed on the sidecar
- Cookie auth is working (`/auth/set-cookie-form`, `samesite=lax`)
- EC2 Info fetches from SP CLI `/catalog/ec2-info` (correct IAM boundary)
- CI pipeline syncs `sg_compute/version` automatically

### What's still broken / old
- `admin/admin.js` calls `/catalog/types` and `/catalog/stacks` (should be `/api/specs` and `/api/nodes`)
- `sp-cli-compute-view.js` has a hardcoded `CATALOG` array (8 entries, missing 4 specs)
- `sp-cli-launcher-pane.js` has a hardcoded `PLUGIN_ORDER` (8 entries)
- `settings-bus.js` `DEFAULTS.plugins` hardcodes 8 spec names
- `sp-cli-nodes-view.js` uses old field names: `stack_name`, `type_id`, `state === 'running'`

---

## 4. The one risk that will bite you in F2

`Schema__Node__Info` (returned by `GET /api/nodes`) does **not** include
`host_api_url`, `host_api_key`, or `host_api_key_vault_path`. These fields
currently come from `/catalog/stacks` and drive the Terminal, Host API, and
Pods tabs in `sp-cli-nodes-view`.

**Recommended fix (lowest friction):** derive on the frontend.

In `sp-cli-nodes-view.js`, replace all reads of `stack.host_api_url` with:
```js
const hostUrl = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
```
This is already the fallback pattern in the code — just make it the primary.
For `host_api_key`, the vault fallback via `currentVault().read(vaultPath)` is
also already coded. These two fallbacks are sufficient to make the tabs work
without any backend schema change.

After applying this, F2 can switch the data source cleanly.

---

## 5. Recommended sequence

### F2 first (not F1)

The brief recommends F1 (copy-edit) first, but given the field-name mismatch
risk, doing F2 first is safer: wire the new endpoints, verify data flows, then
do F1 copy-edits on the now-correct code. F1 on broken data is wasted effort.

**F2 checklist:**

- [ ] `admin/admin.js` lines ~259–260: `/catalog/types` → `/api/specs`, `/catalog/stacks` → `/api/nodes`
- [ ] `sp-cli-nodes-view.js`: `stack.stack_name` → `stack.node_id`, `stack.type_id` → `stack.spec_id`
- [ ] `sp-cli-nodes-view.js`: `state === 'running'` — verify what value `/api/nodes` actually returns (may be `'running'`, `'ready'`, or `'READY'`; check `Schema__Node__Info` in `sg_compute/core/node/schemas/`)
- [ ] `sp-cli-nodes-view.js`: apply the `host_api_url` / `host_api_key` fallback pattern (§4 above)
- [ ] Verify in browser DevTools: Network tab shows `/api/nodes` (not `/catalog/stacks`)

### Then F5

- [ ] Create `shared/spec-catalogue.js`: fetches `GET /api/specs`, caches for page lifetime, emits `sp-cli:catalogue.loaded`
- [ ] `sp-cli-compute-view.js`: delete `CATALOG` constant; use `getCatalogue().specs`
- [ ] `sp-cli-launcher-pane.js`: delete `PLUGIN_ORDER`; iterate `getCatalogue().specs`
- [ ] `settings-bus.js`: remove hardcoded 8-entry `DEFAULTS.plugins`; populate from catalogue on first load

### Then F1

- [ ] User-visible strings: "Stack" → "Node", "Plugin" → "Spec", "Container" → "Pod"
- [ ] Do NOT rename: web component tag names, event names, CSS classes, file names

---

## 6. Key files

```
sgraph_ai_service_playwright__api_site/
  admin/
    admin.js                          ← change /catalog/types + /catalog/stacks here
  shared/
    api-client.js                     ← HTTP client (no changes needed)
    catalog.js                        ← OLD — supersede with spec-catalogue.js
    settings-bus.js                   ← remove hardcoded DEFAULTS.plugins
  components/sp-cli/
    sp-cli-compute-view/              ← delete static CATALOG
    sp-cli-launcher-pane/             ← delete PLUGIN_ORDER
    sp-cli-nodes-view/                ← fix field names (stack_name→node_id etc.)
    sp-cli-settings-view/             ← mostly done; verify copy text
sg_compute/core/node/schemas/         ← check Schema__Node__Info for exact state values
```

---

## 7. Verify state vocabulary before writing a single line of F2

Before changing `state === 'running'` in `sp-cli-nodes-view`, check what the
real API returns:

```bash
grep -r "state\|State__Node\|Enum__Node" sg_compute/core/node/schemas/ --include="*.py" | grep -v __pycache__
```

If state values are `'running'` (lowercase) the current code is fine and no
change is needed. If they are `'ready'` or `'READY'`, update every `=== 'running'`
check in `sp-cli-nodes-view.js` at the same time as F2. Do NOT leave this for
a later phase — a silent mismatch means nodes always look non-running.

---

## 8. Branch and PR convention

Per the brief:
- Branch: `claude/sg-compute-frontend-{phase}-{description}-{session-id}`
- One PR per phase, tagged `phase-F{N}__short-name`
- Do NOT push to `dev` directly

---

## 9. What NOT to touch

- `sg_compute/host_plane/fast_api/` — sidecar is done
- `Routes__Host__Auth`, `Routes__Host__Docs`, `Routes__Host__Shell` — done
- `.github/workflows/` — CI is done
- `sgraph_ai_service_playwright/fast_api/` — Playwright Lambda service, unrelated
