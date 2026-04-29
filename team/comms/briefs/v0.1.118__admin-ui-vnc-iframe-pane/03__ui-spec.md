# 03 — UI spec

## When the pane appears

The new "VNC viewer" pane appears in the right-hand column **only when the
selected stack is type `VNC` and state is `RUNNING`**. For other stack
types or non-running VNC stacks, the pane is hidden (or shows an empty
state explaining why).

Suggested placement: same column as `Stack Detail` — either as a tab
alongside it (`Stack Detail | Viewer | Mitmweb`) or as a stacked pane
below it. The screenshot already shows tabs at the top of that column —
add `Viewer` and `Mitmweb` next to `Stack Detail`.

## Pane states

| State | Trigger | UI |
|---|---|---|
| `Stack not running` | `state ≠ RUNNING` or `nginx_ok=false` | "Stack is starting — health: nginx no / mitmweb no. Polling…" |
| `Cert not trusted` | First time the operator opens this stack | Placeholder + "Open in new tab to trust the cert" button |
| `Auth needed` | Password not in vault for this stack | One-shot input field, store in vault on submit |
| `Ready` | Cert trusted + auth in vault | iframe mounted, fills the pane |

## Controls

Inside the pane header:

- **Refresh** — `iframe.contentWindow.location.reload()` (forces noVNC reconnect)
- **Open in new tab** — same URL, target `_blank`. Useful for "I want to
  drag-and-drop a file in" or "I want full-screen".
- **Copy URL** — hand the operator the bare URL for sharing in a ticket.
- **Mitmweb toggle** — switches the iframe between the chromium viewer
  and the mitmweb flows UI. (Or: split-pane both. Operator preference.)

## Stack Detail integration

On the `Stack Detail` pane (right column today, screenshot), add two
buttons under the existing fields:

```
[ Open Viewer ]   [ Open Mitmweb ]
```

Clicking either one switches the right-column tab to the corresponding
iframe pane. The destructive `Delete stack` button stays at the bottom
where it is.

## Loading + reconnect behaviour

- noVNC handles its own websocket reconnect — if the iframe is mounted
  and the EC2 reboots, the operator just sees a brief disconnect overlay.
- If the stack is **deleted** while the iframe is open, show a banner
  over the iframe: "Stack was deleted — viewer is no longer available."
  Listen on the existing stack-status websocket (Activity Log feed).

## Sizing

The pane should fill its container. The chromium viewer scales internally
(noVNC's `scale=remote` mode). Default width: whatever the column gives;
default height: at least 600px so the chromium toolbar + page are usable.
A "fullscreen" toggle that hides the catalog / stacks columns is a nice-
to-have.
