# 02 — Login page spec

## Layout

A single Tailwind / system-CSS page, one column, ~440px wide on desktop.
Renders cleanly inside the admin-UI iframe pane (no fixed-position
overlays).

```
┌─────────────────────────────────────┐
│                                     │
│   [SG/Send logo]                    │
│                                     │
│   sp vnc · vnc-clever-noether       │
│   Region: eu-west-2 · t3.large      │
│                                     │
│   ─────────────────────────         │
│                                     │
│   Operator password                 │
│   [    ____________________   ]     │
│                                     │
│   [ ] Remember me on this browser   │
│                                     │
│   [        Sign in        ]         │
│                                     │
│   ─────────────────────────         │
│                                     │
│   Help? See `sp vnc --help`         │
│                                     │
└─────────────────────────────────────┘
```

## What the page knows about the stack

The sidecar is per-EC2 — it can render the stack name + region directly
from env vars set at boot:

| Env var (already set in user-data) | Used for |
|---|---|
| `STACK_NAME` | shown in the heading |
| `REGION`     | shown as a subtitle |
| `INSTANCE_TYPE` (new) | shown as a subtitle |

This grounds the operator: "yes, I'm signing into the right stack". Without
it, the popup-style Basic auth prompt is a black box.

## Error states

| Trigger | Page behaviour |
|---|---|
| Wrong password | Re-render the form with a red banner: "That password didn't match. Try again." Form retains focus on the password field. Add a 1-second debounce server-side to soft-rate-limit. |
| Empty password | Inline validation, no server round-trip. |
| Already signed in (cookie valid) | Redirect to `next` query param (defaults to `/`). |
| Session expired | Banner: "Your session expired — please sign in again." (set by `/auth` setting a cookie that the redirect reads.) |

## Branding hooks

- `<title>SG/Send · sp vnc · {stack_name}</title>`
- favicon: ship the SG/Send `static/images/favicon.ico` in the sidecar image.
- One CSS file embedded in the HTML — no external requests, so the page
  works even if the operator's network blocks CDN domains.
- Logo as inline SVG so it tints with `currentColor` if we add dark mode.

## Accessibility

- `<form>` posts to `/login`; works without JS.
- `aria-invalid` on the password field on retry.
- `<label for>` on the password input.
- Enter submits.

## Logout

A `POST /logout` endpoint clears the cookie and redirects to `/login`.
The chromium viewer's noVNC top bar can call this via a small "Sign out"
link injected by the admin UI iframe pane (out of scope for this brief —
the admin UI owns its own logout button).

For users hitting the EC2 directly without the admin UI, add a small
unobtrusive `Sign out` link in the top-right corner of the chromium
viewer overlay — OR accept that direct-access users use browser cookie
controls. Decision in `04__decision.md`.
