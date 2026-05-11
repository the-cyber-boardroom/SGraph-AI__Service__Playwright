# SKILL: SG/Playwright Screenshot Service — Agent Integration Guide

## Overview

This skill gives any Claude agent the ability to take **live screenshots of sgraph.ai pages**
using the `dev.sg-playwright.sgraph.ai` REST API — a hosted Playwright service that runs a
real Chromium browser on demand. No local Playwright installation, no Selenium, no headless
browser setup required.

**Service base URL:** `https://dev.sg-playwright.sgraph.ai`
**Auth:** Requires a custom header (provided separately — do not store in this file).

---

## Authentication

Every request must include this HTTP header:

```
api-key__for__SGraph-AI__App__Send: <VALUE_PROVIDED_BY_OPERATOR>
```

The header name is non-standard (it is not `Authorization`). Get the value from the operator
or from the secure context in which this agent is running. Without it, every call returns 401.

---

## Core Concept: Sequences

The primary endpoint is `POST /sequence/execute`. A sequence is a list of browser steps
(navigate, wait, screenshot, etc.) that run in order inside a single browser session.
The session is created and torn down automatically per request.

### Minimal working example — screenshot a page

```json
POST https://dev.sg-playwright.sgraph.ai/sequence/execute
Content-Type: application/json
api-key__for__SGraph-AI__App__Send: <YOUR_KEY>

{
  "capture_config": {
    "screenshot": {"enabled": true, "sink": "inline"},
    "include_execution_result": true
  },
  "sequence_config": {
    "halt_on_error": false,
    "total_timeout_ms": 60000
  },
  "steps": [
    {"action": "navigate", "url": "https://qa.sgraph.ai/en-gb/library/", "wait_until": "networkidle"},
    {"action": "screenshot", "save_as": "page.png"}
  ],
  "close_session_after": true
}
```

The response includes the screenshot as a base64-encoded PNG in:
`response.step_results[N].artefacts[0].inline_b64`

A top-level `response.artefacts` array also collects all artefacts from the sequence.

---

## Critical: `wait_until` — use `networkidle`, not the default

The `navigate` step defaults to `wait_until: "load"`, which fires on the DOM load event.
**sgraph.ai pages are JS-rendered — the load event fires before dynamic content appears.**

Always use:
```json
{"action": "navigate", "url": "...", "wait_until": "networkidle"}
```

`networkidle` waits until no network activity for 500ms after navigation — this gives JS
frameworks time to fetch and render content. Typical page load time jumps from ~500ms to
~2–3 seconds, but the screenshot will actually contain the rendered content.

The three `wait_until` values:
- `load` — DOM load event (default, too early for JS pages)
- `domcontentloaded` — even earlier, rarely useful
- `networkidle` — **use this for all sgraph.ai pages**

---

## Available Step Types

| Step action | What it does | Key fields |
|---|---|---|
| `navigate` | Go to a URL | `url`, `wait_until` |
| `screenshot` | Capture PNG | `save_as`, `full_page`, `selector` |
| `wait_for` | Wait for a CSS selector to appear | `selector`, `visible`, `timeout_ms` |
| `get_content` | Return page text or HTML | `content_format: "text"` or `"html"` |
| `get_url` | Return current URL | — |
| `click` | Click an element | `selector`, `button` |
| `fill` | Fill a form field | `selector`, `value` |
| `scroll` | Scroll page or element | `selector`, `x`, `y` |
| `evaluate` | Run JS expression (allowlist-gated) | `expression`, `return_type` |
| `set_viewport` | Change viewport size | `width`, `height` |

---

## Recommended Sequence for sgraph.ai Pages

```json
{
  "capture_config": {
    "screenshot": {"enabled": true, "sink": "inline"},
    "include_execution_result": true
  },
  "sequence_config": {"halt_on_error": false, "total_timeout_ms": 60000},
  "steps": [
    {
      "action": "navigate",
      "url": "https://qa.sgraph.ai/en-gb/SECTION/PAGE/",
      "wait_until": "networkidle"
    },
    {
      "action": "wait_for",
      "selector": "#content-ready",
      "timeout_ms": 8000,
      "visible": true
    },
    {
      "action": "screenshot",
      "save_as": "page.png",
      "full_page": false
    }
  ],
  "close_session_after": true
}
```

Note: The `wait_for #content-ready` step only works once the sgraph.ai site adds a sentinel
element (see Brief 2 — Dev brief for the site). Until then, `networkidle` alone is sufficient.

---

## Reading Page Content (for issue triage, not just screenshots)

You can use `get_content` to extract text from a page for analysis:

```json
{
  "steps": [
    {"action": "navigate", "url": "https://qa.sgraph.ai/en-gb/dev/issues/", "wait_until": "networkidle"},
    {"action": "get_content", "content_format": "text"}
  ]
}
```

The text content appears in `response.step_results[N].content`. This is useful for reading
issue lists, page structure, or verifying content has loaded before screenshotting.

---

## Known sgraph.ai Pages

| Page | URL |
|---|---|
| Library home | `https://qa.sgraph.ai/en-gb/library/` |
| Dev / Issues | `https://qa.sgraph.ai/en-gb/dev/issues/` |
| Dev / Project Status | `https://qa.sgraph.ai/en-gb/dev/` |
| Dev / Workstreams | `https://qa.sgraph.ai/en-gb/dev/workstreams/` |
| Dev / Agents | `https://qa.sgraph.ai/en-gb/dev/agents/` |

All pages require `wait_until: "networkidle"` to render dynamic content.

---

## Parsing the Response

```python
import json, base64

data = json.loads(response_text)

# Check overall status
assert data["status"] == "completed"

# Extract screenshot from a specific step
for step in data["step_results"]:
    if step["action"] == "screenshot":
        for artefact in step["artefacts"]:
            png_bytes = base64.b64decode(artefact["inline_b64"])
            # write to file, display, or pass to vision model

# Extract text content
for step in data["step_results"]:
    if step["action"] == "get_content":
        text = step.get("content", "")
```

---

## Gotchas

1. **The auth header name is unusual** — it is `api-key__for__SGraph-AI__App__Send`, not
   `Authorization` or `X-API-Key`. Copy it exactly.

2. **`halt_on_error: false` is safer for sequences with `wait_for`** — if a selector does
   not exist yet, the step fails but the sequence continues to the screenshot step.

3. **`sink: "inline"` is required to get the image back in the response.** Other sinks
   (vault, s3, local) write the file elsewhere and return only a reference.

4. **The service is stateless between requests** — each `POST /sequence/execute` starts a
   fresh browser session. There is no persistent state unless you manage session IDs manually.

5. **`full_page: false` (default) captures only the viewport.** Use `full_page: true` for
   long pages, but be aware this produces much larger images.

6. **The service is deployed on Lambda** — cold starts can add 1–2s on the first call after
   idle. Subsequent calls within a short window will be faster.

7. **`networkidle` timeout** — if a page has polling or a websocket keeping the connection
   alive, `networkidle` may never fire and will fall back to `timeout_ms`. If a page hangs,
   reduce `total_timeout_ms` or switch to `wait_for` a specific selector.

---

## Service Health Check

```
GET https://dev.sg-playwright.sgraph.ai/health/status
api-key__for__SGraph-AI__App__Send: <YOUR_KEY>
```

Returns service capabilities, deployment environment, and browser availability.

---

## Current Known Issues on qa.sgraph.ai (as at v0.2.0)

| ID | Title | Status | Priority |
|---|---|---|---|
| I-001 | Footer — minimise legacy content, add deployment version info | OPEN | MEDIUM |
| I-002 | Nav buttons LIBRARY/DEV shift position on selection | OPEN | HIGH |
| I-003 | CRITICAL — Dev section pages failing to load content | IN-PROGRESS | CRITICAL |

Issue I-003 means some Dev section pages may return incomplete content even with `networkidle`.
If a screenshot looks blank or partially loaded, this is a known site issue, not a service issue.
