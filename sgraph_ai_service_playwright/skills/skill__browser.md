# SKILL — sg-playwright (browser agent)

_Status: FIRST-PASS PLACEHOLDER (v0.1.29). TODO — expand before v0.2._

## Who this is for

An autonomous browsing agent that wants to drive `sg-playwright` over HTTP to
interact with web pages on its behalf. You do not need MCP; the API is plain
REST with Type_Safe JSON schemas.

## Start here

1. `GET /admin/manifest` — returns the entry points (OpenAPI, capabilities,
   SKILL files keyed by audience).
2. `GET /openapi.json` — fetch the route catalogue. Every request/response is
   typed; no free-form payloads.

## Core building blocks (stateless)

- `POST /browser/navigate` `{ url, headless, timeout_ms }` — goto a URL.
- `POST /browser/click`    `{ url, selector, … }` — click and return result.
- `POST /browser/fill`     `{ url, selector, value, … }` — fill a field.
- `POST /browser/get-content` — return rendered HTML.
- `POST /browser/get-url` — return current URL after redirects.
- `POST /browser/screenshot` — return a PNG artefact.

Each one-shot endpoint launches a fresh browser, runs the step, tears down.
There is no wire-visible session ID you need to carry.

## Composite flows

- `POST /sequence/execute` — send a whole `Schema__Sequence` payload. Use this
  when you need state to persist across multiple steps (e.g. login → navigate
  → screenshot → extract content).

## Contract guarantees

- No arbitrary JS execution. `evaluate` is allow-list gated; the default
  allow-list is empty.
- Every response is a Type_Safe schema — shape is stable across patch versions.
- Errors return non-2xx HTTP + a structured body, never a stack trace.

## TODO before v0.2

- Worked examples: login → grab cookie → re-use in later `/browser/*` calls.
- Typical timeout / retry recipes.
- How to interpret `/admin/capabilities → declared_narrowing` once lockdown
  layers land.
