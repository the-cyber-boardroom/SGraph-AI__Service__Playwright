# WS Shell Stream — Auth Gap

**Version context:** v0.1.154
**Status:** PROPOSED — backend change needed

---

## Problem

The `/host/shell/stream` WebSocket endpoint on the sidecar (`Fast_API__Host__Control`) is
gated by the same `_Middleware` subclass that checks for `X-API-Key` on every HTTP request.

Browsers **cannot** send custom headers during a WebSocket upgrade (the `Upgrade` request
goes through `XMLHttpRequest`/`WebSocket` API with no header injection allowed). The result
is a `403` / `1006` close code immediately on connection.

The UI (`sp-cli-host-shell`) detects code `1006` and:

1. Writes an explanatory message into the xterm terminal.
2. Auto-expands the Quick Commands panel as a fallback.

The interactive terminal is therefore non-functional until the backend is fixed.

---

## Proposed Fix

**Option A — query param fallback in middleware (preferred)**

Extend `setup_middleware__api_key_check()` so the `_Middleware.dispatch()` method also
accepts `?api_key=<value>` as a fallback, checked only when `X-API-Key` is absent:

```python
api_key = request.headers.get("X-API-Key") \
          or request.query_params.get("api_key")
```

This is safe when applied only to WS paths; the standard HTTP routes continue to require
the header. The UI connects via:

```
ws://{host}:19009/host/shell/stream?api_key={encodeURIComponent(key)}
```

**Option B — exclude from middleware, auth inside handler**

Remove `/host/shell/stream` from middleware coverage entirely and validate the key as the
first step of the WebSocket handler (query param check, close with 4401 if absent/wrong).

---

## Scope

- File: `sgraph_ai_service_playwright__cli/elastic/service/Fast_API__Host__Control.py`
  (or wherever `setup_middleware__api_key_check` lives for the sidecar)
- No change to the Playwright service itself.
- The UI change is already shipped: `sp-cli-host-shell` v0.1.0 connects with `?api_key=`
  and handles the `1006` fallback gracefully.

---

## Until This Is Fixed

The xterm terminal shows:

```
Session ended
⚠ WS auth not yet supported — use Quick Commands below
```

The Quick Commands panel auto-expands. All existing quick-command functionality continues
to work via `POST /host/shell/execute` with the `X-API-Key` header.
