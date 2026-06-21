---
title: "03 — Workflow authoring (import / export / share)"
file: 03__workflow-authoring.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED — format design, no runtime code
parent: README.md
covers: "User point (c) — workflow import/export"
---

# 03 — Workflow authoring

Covers **point (c)**: saving, loading, sharing, and exporting workflows. The guiding
constraint is **Decision #3** — a workflow IS a `/sequence/execute` (or batch /
inspect) request body plus a thin metadata envelope. No bespoke DSL, no translation
layer, lossless round-trip. **Client-only** (Q2 default): localStorage + file
up/download. Zero backend.

---

## 1. The on-disk / exchange format

A workflow file is JSON with two top-level keys: an envelope and the raw request body.

```json
{
  "sg_playwright_workflow": {
    "format_version": "1",
    "title":          "Login then extract",
    "description":    "Authenticated navigate + get_text",
    "endpoint":       "/sequence/execute",
    "created_at":     "2026-06-21T00:00:00Z",
    "service_version_seen": "v0.2.63"
  },
  "request": {
    "capture_config": {},
    "sequence_config": {},
    "steps": [
      { "action": "navigate", "url": "https://app.example.com/login" },
      { "action": "get_text", "selector": "main" }
    ]
  }
}
```

Rules:

- **`request` is verbatim the body** the UI would POST. For `endpoint:
  "/sequence/execute"` it validates against `Schema__Sequence__Request`; for
  `/screenshot/batch` against `Schema__Screenshot__Batch__Request`; for `/inspect`
  against `Schema__Inspect__Request`. The envelope never alters the body.
- **`endpoint`** is one of the workflow-bearing routes:
  `/sequence/execute`, `/screenshot`, `/screenshot/batch`, `/inspect`. (`/session/*`
  is a multi-call flow — see §5.)
- **`format_version`** is a plain string (`"1"`), bumped only on a breaking envelope
  change. The `request` body's own compatibility is the service's `Schema__*` — the
  envelope does not version it.
- **No secrets.** The API key and the vault `credentials` block are **stripped on
  export** (§4). A workflow file is shareable; it carries no auth material.

---

## 2. Round-trip guarantee

The console must satisfy: **build → export → re-import → build === identical request
body.**

- Export serialises the exact JS object the builder would POST (after the
  secret-strip), pretty-printed.
- Import parses, validates `endpoint` is known, loads `request` into the matching
  tab's builder, and re-renders every step from `request.steps[].action` using the
  same verb→fields table the builder uses (brief 01 §3.2).
- Any field present in `request` but unknown to the builder is **preserved and shown
  in a raw "extra fields" expander** rather than dropped — so a workflow authored
  against a newer service still round-trips through an older console without silent
  loss.
- "Copy as JSON" (Decision #6) emits just the `request` body (no envelope) for
  pasting straight into `curl -d`.

---

## 3. Storage + transport surfaces

| Surface | Mechanism | Notes |
|---------|-----------|-------|
| **Save (local)** | `localStorage` under `sg_playwright_workflows` (a JSON map `title → workflow file`) | survives reload; same store the current page uses for the API key (`Routes__Index.py:288`) |
| **Load (local)** | dropdown of saved titles → loads into builder | per-browser; no sync |
| **Export file** | `Blob` + `download` attr → `<title>.sgpw.json` | the §1 format; secret-stripped |
| **Import file** | `<input type=file>` → parse → validate → load | rejects unknown `endpoint`; shows parse errors inline |
| **Copy as curl** | `curlExporter()` (brief 01 §4) | builds `curl -X POST <API_BASE><endpoint> -H 'Content-Type: application/json' -H '<auth-header>: <KEY>' -d '<request>'`; the auth header matches the selected mode (Decision #7); **`<KEY>` is rendered as the literal placeholder, never the stored key** |
| **Copy as JSON** | clipboard ← `request` body only | for pasting into another tool |
| **Share link** | `#wf=<base64url(workflow file)>` in the URL hash | client-only; the page reads `location.hash` on load and offers "import shared workflow"; **size-capped** (~8 KB) — larger workflows must use file export |

> The share link uses the URL **fragment** (`#`), never a query string — fragments are
> not sent to the server, keeping workflows client-side. It is secret-stripped like
> every other export.

---

## 4. Secret handling (non-negotiable)

`Routes__Index.py:288-291` already stores the API key in localStorage. Workflows must
**never** capture it:

1. On export / copy-curl / share, the exporter deep-strips:
   - the API key (it lives outside `request`, in the auth panel — never serialised),
   - the `request.credentials` block (vault cookies / storage state / headers) — set
     to `null` with a "credentials removed on export" note in the envelope.
2. Copy-as-curl renders the auth header value as a **placeholder** (`$SG_TOKEN`), not
   the stored key, so a shared curl line is safe to paste in chat.
3. CLAUDE.md rules #12/#13: no AWS creds, no vault keys in any file. A workflow file is
   data, not code; the strip guarantees it stays shareable.

---

## 5. The `/session/*` multi-call case

A session flow is not a single body, so the envelope's `endpoint` is `/session` and
`request` becomes an ordered list of `{ phase, body }`:

```json
{
  "sg_playwright_workflow": { "format_version": "1", "endpoint": "/session", "title": "Stateful probe" },
  "request": {
    "session": [
      { "phase": "open",  "body": { "browser_config": {} } },
      { "phase": "act",   "body": { "steps": [ { "action": "navigate", "url": "https://app.example.com" } ] } },
      { "phase": "probe", "body": { "settle": [], "probes": { "url": { "action": "get_url" } } } },
      { "phase": "close", "body": {} }
    ]
  }
}
```

The Session tab replays the phases in order, substituting the live `session_id` into
the `act`/`probe`/`close` URLs. Round-trip and secret-strip rules apply identically.

---

## 6. What this enables

- The brief 02 gallery ships as **bundled `.sgpw.json` files** (the envelope's `title`
  + `request`) loaded from a static `WORKFLOWS` JS array inside `INDEX_HTML` — no
  separate asset route needed (Decision #1).
- The same files are the integration-test fixtures (brief 06): a test loads the
  `request` body and POSTs it, asserting on the response. Because the format IS the
  request body, the fixture and the UI run identical JSON.
- A user can author a workflow once, export it, hand it to a teammate or an agent, and
  it runs byte-identically via `curl` or via another console — the format is the API.
