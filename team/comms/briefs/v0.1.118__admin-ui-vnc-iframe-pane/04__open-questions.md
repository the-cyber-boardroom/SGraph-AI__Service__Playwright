# 04 — Open questions

Decisions for the admin-ui team to make. None block the work — but worth
agreeing up front so the first PR doesn't immediately need a follow-up.

1. **Tabs vs stacked panes** — does `Viewer` go as a tab alongside
   `Stack Detail` (compact, single pane visible at a time) or as a second
   pane stacked underneath (always visible, always loading the iframe)?

2. **Mitmweb in same pane or separate** — toggle inside one pane, or
   two parallel panes (Viewer + Mitmweb)?

3. **Password storage** — reuse the existing vault (the `86b226575882`
   key on the top right) keyed by `stack_name`, or session-only storage
   (sessionStorage)?

4. **CLI-created stacks without UI password capture** — the CLI prints
   the password once and the operator stashes it manually. When such a
   stack appears in the UI, do we:
   - (a) Prompt the operator to paste the password the first time they
     click `Open Viewer`, then stash it in the vault? OR
   - (b) Refuse to embed and show "Open in new tab" only, since we don't
     have the password?

5. **Auto-pre-warm auth on stack create-from-UI** — when the user hits
   "Launch" on the VNC catalog tile, the UI knows the password (it just
   generated/received it). Should the UI immediately do the
   pre-warm fetch (Approach B in `02__auth-flow.md`) so the iframe loads
   without a prompt? My assumption: yes.

6. **Self-signed cert UX** — the one-time "open in new tab to trust"
   step is unavoidable with the current backend. If we want to remove
   it, the backend slice would be: provision Caddy with the `internal`
   ACME endpoint OR run nginx with a real Let's Encrypt cert via DNS-01
   on a wildcard subdomain. Out of scope for this brief; flag it as a
   **followup** if the trust-prompt UX bothers users.

7. **Backend API needed?** — current admin UI talks to `sp` over HTTP
   (assumed). Does the UI need a new backend endpoint to fetch
   `viewer_url + mitmweb_url + password`, or can it derive everything
   from `public_ip` + the vault entry?
