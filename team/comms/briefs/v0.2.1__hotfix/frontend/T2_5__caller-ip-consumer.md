# T2.5 — Replace deleted ipify call (FV2.11 deleted without replacement)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

FV2.11 brief required the `api.ipify.org` external call to be **replaced**, not just deleted. Two options were specified:

- Option A — backend `/catalog/caller-ip` endpoint that detects the caller's IP server-side.
- Option B — local heuristic (e.g. `localhost` → `127.0.0.1`; otherwise prompt the operator).

The dev chose **neither**. Just removed the row outright. **Privacy goal achieved, UX regressed, no backend ticket filed.**

## Why it matters

The caller IP was used for SG ingress allowlist on EC2 (so the operator could reach the launched Node from their own machine). Without it, operators have to type their IP every time, OR the launch silently uses `0.0.0.0/0` (open to the world — security regression).

## Tasks

1. **Decide with Architect: Option A or Option B** (recommend Option A — keeps the operator UX clean).
2. **Option A path:**
   - File a backend follow-up brief (`team/comms/briefs/v0.2.1__hotfix/backend/T3_X__caller-ip-endpoint.md`) for `GET /catalog/caller-ip`. Backend reads the `X-Forwarded-For` header (CF / Lambda Web Adapter sets it).
   - Frontend implements the consumer: `apiClient.get('/catalog/caller-ip')` populates the field at form load.
   - **PARTIAL marker on this PR** until the backend route ships. Document in PR description.
3. **Option B path:**
   - Local heuristic in `sg-compute-launch-form.js`: if `window.location.hostname` matches `localhost|127.0.0.1|0.0.0.0`, use `127.0.0.1`. Otherwise, leave the field empty + show a clear placeholder + helper text "Enter your public IP — find it at https://www.google.com/search?q=what+is+my+ip".
4. **Restore the field** in the launch form (was deleted in FV2.11). Position above instance size; pre-populate per the chosen Option.
5. **Test** — open the form locally; verify the field populates correctly.

## Acceptance criteria

- Caller IP appears in the launch form (was missing post-FV2.11).
- Source is either backend `/catalog/caller-ip` or local heuristic per Architect call.
- No third-party origin called from the dashboard.
- Form smoke test: launching a Node uses the expected caller IP.

## "Stop and surface" check

If the backend endpoint is going to take more than this session: **STOP** and ship Option B as an interim fix; file the Option A follow-up brief. Don't ship without ANY caller-IP UX.

## Live smoke test (acceptance gate)

Open the launch form. The caller-IP field is populated with a sensible default. Submit a launch; the resulting Node's SG allowlist contains that IP. Screenshot.

## Source

Executive review Tier-2; frontend-late review §"Missed requirement #3 (FV2.11)".
