# Brief: Feature Requests — dev.sg-playwright.sgraph.ai Service

**To:** Playwright Service Dev team
**From:** Conductor / Infrastructure (via hands-on integration work)
**Re:** New step types and quality-of-life improvements for automation script authors
**Version:** Against current API v0.20.55
**Date:** 2026-05-08

---

## Context

These feature requests come directly from writing real automation sequences against
`qa.sgraph.ai` — a JS-rendered site with dynamic content loading. The current service is
excellent for basic navigate+screenshot, but authoring reliable sequences for JS-heavy pages
requires workarounds. Each request below addresses a specific pain point encountered in practice.

---

## Feature Request 1 — `wait_for_function` step (HIGH PRIORITY)

### Problem
`wait_for` with a `selector` waits for a DOM element. But many JS apps signal readiness via
a global flag (e.g. `window.__playwright_ready = true`) rather than a DOM element. There is
currently no way to poll a JS expression until it returns truthy.

### Proposed schema

```python
class Schema__Step__Wait_For_Function(Schema__Step__Base):
    action       : Enum__Step__Action = Enum__Step__Action.WAIT_FOR_FUNCTION
    expression   : Safe_Str__JS__Expression          # e.g. "window.__playwright_ready === true"
    return_type  : Enum__Evaluate__Return_Type = Enum__Evaluate__Return_Type.BOOLEAN
    polling_ms   : Safe_UInt__Milliseconds = 100     # How often to poll
    timeout_ms   : Safe_UInt__Timeout_MS = 30_000
```

### Usage

```json
{"action": "wait_for_function", "expression": "window.__playwright_ready === true", "timeout_ms": 10000}
```

### Playwright backing call
`page.wait_for_function("window.__playwright_ready === true", timeout=10000)`

### Notes
- The `expression` field should go through the same JS allowlist as `evaluate`, but the
  allowlist may need to include simple boolean property accesses (`window.X === true/false`).
- This is the canonical Playwright idiom for "wait for app to finish rendering".
- Strongly paired with Brief 2 (site adds `window.__playwright_ready` flag).

---

## Feature Request 2 — `wait` step (fixed delay) (MEDIUM PRIORITY)

### Problem
There is no way to insert a simple fixed-duration pause in a sequence. Sometimes you need
to wait 1–2 seconds after an action for animations to complete or lazy content to render,
without a specific selector to wait for.

### Proposed schema

```python
class Schema__Step__Wait(Schema__Step__Base):
    action       : Enum__Step__Action = Enum__Step__Action.WAIT
    duration_ms  : Safe_UInt__Milliseconds = 1000    # Max cap recommended: 10_000
```

### Usage

```json
{"action": "wait", "duration_ms": 2000}
```

### Notes
- Simple wrapper around `asyncio.sleep(duration_ms / 1000)` or `page.wait_for_timeout()`.
- Should be capped (suggest 10_000ms max) to prevent sequences hanging indefinitely.
- This is a last resort — `wait_for_function` and `wait_for` selector are preferable —
  but it's essential for sequences where readiness signals don't yet exist on the page.

---

## Feature Request 3 — `scroll_to_bottom` convenience step or `scroll` enhancement (LOW PRIORITY)

### Problem
To screenshot long pages with lazy-loaded content, you need to scroll to trigger loading
before taking the screenshot. The current `scroll` step requires explicit `x`/`y` values,
which means you need to know the page height. There's no "scroll to bottom" shorthand.

### Proposed addition to `Schema__Step__Scroll`

```python
class Schema__Step__Scroll(Schema__Step__Base):
    action   : Enum__Step__Action = Enum__Step__Action.SCROLL
    selector : Safe_Str__Selector = None
    x        : Safe_Int = 0
    y        : Safe_Int = 0
    to_bottom: bool = False          # NEW: if True, scroll to document bottom
```

### Usage

```json
{"action": "scroll", "to_bottom": true}
```

### Playwright backing call
`page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`

---

## Feature Request 4 — Step-level `wait_after_ms` field on all steps (MEDIUM PRIORITY)

### Problem
After a `click` or `navigate`, you often want to wait a short time for the UI to settle
before the next step. Currently this requires inserting a separate `wait` step between every
action. A `wait_after_ms` field on `Schema__Step__Base` would be much cleaner.

### Proposed addition to `Schema__Step__Base`

```python
class Schema__Step__Base(Type_Safe):
    id               : Step_Id = None
    continue_on_error: bool    = False
    timeout_ms       : Safe_UInt__Timeout_MS = 30_000
    wait_after_ms    : Safe_UInt__Milliseconds = 0    # NEW: pause after step completes
```

### Usage

```json
{"action": "navigate", "url": "https://...", "wait_until": "networkidle", "wait_after_ms": 1000},
{"action": "screenshot", "save_as": "page.png"}
```

### Notes
- Applied after the step succeeds, before the next step begins.
- `wait_after_ms: 0` (default) means no change to existing behaviour.
- Max cap recommended (suggest 5_000ms).

---

## Feature Request 5 — `screenshot` step: `wait_for_selector` shorthand (LOW PRIORITY)

### Problem
A very common pattern is:
```json
{"action": "wait_for", "selector": "#content-ready"},
{"action": "screenshot", "save_as": "page.png"}
```

This could be collapsed to a single step to reduce sequence verbosity.

### Proposed addition to `Schema__Step__Screenshot`

```python
class Schema__Step__Screenshot(Schema__Step__Base):
    action           : Enum__Step__Action = Enum__Step__Action.SCREENSHOT
    full_page        : bool = False
    selector         : Safe_Str__Selector = None
    save_as          : Safe_Str__File__Name = None
    wait_for_selector: Safe_Str__Selector = None    # NEW: wait for this selector before capturing
    wait_timeout_ms  : Safe_UInt__Timeout_MS = 10_000  # NEW: timeout for the wait
```

### Usage

```json
{"action": "screenshot", "save_as": "page.png", "wait_for_selector": "#content-ready"}
```

---

## Feature Request 6 — `get_content` result in step_result schema (HOUSEKEEPING)

### Problem (minor)
The `get_content` step result uses a custom `Schema__Step__Result__Get_Content` but the
field name for the content varies slightly in documentation vs. actual response. A clear,
documented field name (`content`) and explicit type (`str`) in the schema would make this
unambiguous for script authors.

### Request
Confirm and document that `Schema__Step__Result__Get_Content.content` is always a `str`,
always present (empty string if nothing matched), and never `null`.

---

## Priority Summary

| # | Feature | Priority | Effort estimate |
|---|---|---|---|
| 1 | `wait_for_function` step | HIGH | Medium — needs allowlist update |
| 2 | `wait` (fixed delay) step | MEDIUM | Low — trivial implementation |
| 4 | `wait_after_ms` on base step | MEDIUM | Low — base class addition |
| 3 | `scroll to_bottom` | LOW | Low |
| 5 | `screenshot.wait_for_selector` | LOW | Low |
| 6 | `get_content` schema clarification | HOUSEKEEPING | Trivial |

**Highest value / lowest effort:** Features 2 and 4 (`wait` step and `wait_after_ms`) can
be shipped immediately and would unblock reliable automation against any JS-heavy page today,
before the site-side changes in Brief 2 are deployed.

**Highest long-term value:** Feature 1 (`wait_for_function`) is the canonical solution and
should be the target architecture once the allowlist is extended to support it.
