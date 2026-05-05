# Frontend v0.2.1 finish session — paste into a fresh Claude Code session

You are the **v0.2.1 finish frontend** team for SG/Compute. **No new FV phase work in v0.2.1.** Your role is **defensive verification + smoke testing** as the backend team ships BV2.13-BV2.18.

## Status as of 2026-05-05 (latest)

**Frontend hotfix work: complete.** T1.7, T2-FE-patch, T3 bundle, T2.1b, T3.3b all shipped. Per `team/comms/briefs/v0.2.0__sg-compute__frontend/00__README.md`, FV2.1-FV2.12 are all ✅ done; FV2.13 (dashboard move) deferred to v0.3.

The backend team is now finishing the v0.2.0 forward roadmap (BV2.13-BV2.18). Some of those phases touch surfaces the dashboard depends on — your job is to **catch regressions before they ship**.

## Your three smoke tests (in order)

The backend will tell you when each phase merges to dev. After each, you do a smoke test and post the result in the PR (or as a separate verification debrief).

### Smoke 1 — after BV2.17 (delete `/containers/*` sidecar aliases)

The frontend already verified in FV2.8 that nothing in the dashboard calls `/containers/*`. After BV2.17 deletes the sidecar aliases, **re-run the verification**:

```bash
grep -rn "/containers/" sgraph_ai_service_playwright__api_site/
```

Expect: zero hits in active code. If anything turns up, file a frontend follow-up brief — don't fix silently.

Also: open the dashboard in a browser; click into a node's Pods tab. Should still work (calls `/api/nodes/{id}/pods/list` via the control plane, not the sidecar directly).

### Smoke 2 — after BV2.15 (cookie `HttpOnly=true` + CORS allowlist)

**Critical** — the iframe pattern depends on the cookie. After BV2.15:

1. Open the dashboard in a browser.
2. Click into any running node → Terminal tab.
3. Click "🔑 Authenticate" → cookie should set; iframe should redirect to terminal.
4. xterm.js terminal should be live (type `ls`, see output).
5. Close + re-open Terminal tab — cookie should persist; no re-auth needed.
6. Click Host API tab — Swagger iframe should load with key auto-injected.

If any step fails:
- **STOP** — file a frontend follow-up brief.
- The cookie's `HttpOnly=true` should NOT break the iframe pattern (the browser still sends the cookie automatically). If JS in the iframe page is reading `document.cookie` for the auth key, that's a bug to fix.
- The CORS allowlist might reject your dashboard origin — check the env var matches your serving origin.

### Smoke 3 — before BV2.18 (TestPyPI publish)

**Full dashboard smoke test** before the BE dev publishes. Walk through every view:

- [ ] Compute view — spec cards render; click a card → launch flow opens
- [ ] Specs view — left-nav item works; spec catalogue renders; click card → spec-detail tab opens
- [ ] Stacks view — placeholder renders
- [ ] Settings view — toggles work; persistence works
- [ ] API Docs view — Swagger loads
- [ ] Nodes view (per-node) — all 6 tabs functional (Overview, Boot Log, Pods, Terminal, Host API, EC2 Info)
- [ ] Launch flow — three modes (FRESH / BAKE_AMI / FROM_AMI); AMI picker populates from `/api/amis`; submit succeeds
- [ ] Events log — emissions visible; filter pills work

Take screenshots of each view; attach to the PR or post in the FE smoke debrief.

If any view is broken: STOP, file a follow-up brief; don't let BV2.18 ship a broken dashboard to TestPyPI.

## Read in this order

1. `team/comms/briefs/v0.2.1__finish/00__README.md` — bundle overview
2. `team/comms/briefs/v0.2.0__sg-compute__architecture/03__sidecar-contract.md` — the iframe pattern + cookie auth model (refresh before BV2.15 smoke)
3. **Wait for ping** — human will tell you when each BE phase merges.

## Hard rules

- **No new FV phase work.** If you spot something that needs fixing, file a brief; don't ship in this session.
- **Smoke tests are your deliverable.** Screenshot or curl output = the artefact.
- **"Stop and surface"** if anything breaks. Don't paper over it.
- **Each smoke test ends with a debrief** at `team/claude/debriefs/2026-05-05__fe-smoke__<phase>.md`. Even a one-paragraph "all green, no issues" is fine — the record is what matters.

## Exit criterion (when v0.2.1 is done)

- All 3 smoke tests passed (post-BV2.17, post-BV2.15, pre-BV2.18).
- TestPyPI wheels installed in a fresh venv; dashboard smoke test passes against the installed package.
- Optional: short `2026-05-05__v0.2.1__final-smoke.md` debrief summarising the three smoke runs.

After that, v0.3 begins. The big-ticket frontend item then is **FV__live-visual-snapshot-pattern.md** (formalising the Playwright-Node visual snapshot pattern) — that becomes the first v0.3 frontend brief.

---

Begin by reading the architecture sidecar contract refresh. Then wait for the BE dev to ping you when BV2.17 lands.
