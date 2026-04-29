# v0.1.118 — Admin UI: VNC iframe pane

**Status:** PROPOSED
**Owner:** admin-ui team
**Audience:** dev wiring up the Admin Dashboard
**Source-of-truth backend:** `sp vnc` (this repo) — see `team/roles/librarian/reality/`

---

## Goal

When a user selects a `VNC` stack in the Admin Dashboard, surface a new pane
that embeds the running chromium-VNC viewer in an `<iframe>` so the operator
can drive the browser without leaving the admin UI.

Stretch (same slice, second iframe): also embed the mitmweb flows UI.

---

## What exists today (backend)

For every running VNC stack, two URLs are reachable from the public internet
(SG ingress on 443, `--open` widens to `0.0.0.0/0`):

| What | URL | Behind |
|---|---|---|
| Chromium-VNC viewer (noVNC) | `https://{public_ip}/` | nginx Basic auth (bcrypt) |
| mitmweb flows UI | `https://{public_ip}/mitmweb/` | same Basic auth |

Both come from the same nginx terminator with a **self-signed cert** generated
at boot. Username is hard-coded to `operator`; the password is whatever the
operator passed via `--password` (or auto-generated, returned ONCE on create).

Backend fields the UI already has on the stack record:
- `public_ip` — e.g. `18.175.190.150`
- `viewer_url` — `https://{public_ip}/`
- `mitmweb_url` — `https://{public_ip}/mitmweb/`
- `state` — must be `RUNNING` and `nginx_ok=true` (probe via `sp vnc health`).

---

## Files in this brief

- `01__embed-mechanics.md` — how the iframe needs to be set up + the self-signed-cert one-time prompt
- `02__auth-flow.md` — how Basic auth is presented and where the password lives
- `03__ui-spec.md` — proposed pane layout, controls, copy
- `04__open-questions.md` — the few decisions we want the admin-ui team to make
