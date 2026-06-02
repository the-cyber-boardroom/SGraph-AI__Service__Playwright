# sg-playwright Debrief — Addendum: A Debug/Probe Execution Model

**from** @Content (Claude session)
**to** the sg-playwright maintainers
**relates to** sg-playwright-debrief.md (the bugs + FR-1..FR-7 feature requests)
**date** 30 May 2026

This addendum answers a question that reframes the original debrief: *can a Claude session
run multiple experiments and hypotheses in a single request?* The honest answer about the
current design — and even about the design with my original FRs implemented — is **not
really**. This document describes the execution model that would make it possible, why it
matters for agent productivity, and the server-side techniques that would make it cheap.

---

## 1. The realisation: my original asks were the wrong shape

The original debrief asked for better *steps* in a *linear sequence*: richer `wait_for`,
DOM reads, etc. But a sequence is a **pipeline of mutations** — do A, then B, then C, halt
if one fails. That's the right model for *acting* on a page (fill form, click, submit).

It is the **wrong** model for *understanding* a page, which is what I spend most of my
"something is wrong" time doing. Debugging is not a pipeline. It's a fan-out of independent
questions asked against a single page state:

- Does selector A exist? B? C? (I have five hypotheses about the right selector.)
- What does `document.querySelectorAll('article').length` return?
- What's in the console right now?
- What failed in the network tab?
- What does the accessibility tree look like under this node?

These questions are **independent, read-only, idempotent, and parallelisable**. In the
current model I either fire five separate requests (five fresh Chromium launches, five
navigations, five decryptions — absurdly wasteful) or chain them as sequence steps with
`halt_on_error:false` and reverse-engineer which passed. Both are clumsy. Neither lets me
ask "of these five selectors, which exist and what do they contain?" in one shot.

**The fix is a different request type: a probe batch against one settled page state.**

---

## 2. The proposed model: `navigate once, probe many`

A new request shape — call it `/pw/inspect` or a `probes` block on `sequence/execute`:

```json
{
  "navigate": { "url": "https://dev.vault.sgraph.ai/#id%3Akey",
                "wait_until": "networkidle", "timeout_ms": 30000 },
  "settle":   { "wait_for": { "any_of": [
                  {"text": "Decrypted"},
                  {"selector_gone": ".spinner"},
                  {"function": "document.querySelectorAll('article').length > 0"}
                ], "timeout_ms": 20000 } },
  "probes": [
    { "id": "h1", "type": "selector_exists", "selector": "sg-page-renderer" },
    { "id": "h2", "type": "selector_exists", "selector": ".page-renderer" },
    { "id": "h3", "type": "selector_exists", "selector": "main article" },
    { "id": "h4", "type": "count",           "selector": "[class*=tab]" },
    { "id": "h5", "type": "eval",            "expression": "document.title" },
    { "id": "h6", "type": "dom_tree",        "root_selector": "body", "max_depth": 3 },
    { "id": "h7", "type": "console_tail",    "lines": 50 },
    { "id": "h8", "type": "network_failures" },
    { "id": "h9", "type": "accessibility_tree", "root_selector": "main" },
    { "id": "a1", "type": "screenshot",      "full_page": true }
  ]
}
```

**One navigation. One settle. Then every probe runs against the same frozen DOM and returns
its own result, keyed by `id`, none halting any other.** Response:

```json
{
  "navigate": {"status":"passed","final_url":"..."},
  "settle":   {"status":"passed","matched":"text:Decrypted","waited_ms":4200},
  "probes": {
    "h1": {"exists": false},
    "h2": {"exists": false},
    "h3": {"exists": true, "count": 1},
    "h4": {"count": 6},
    "h5": {"value": "Private Health Score"},
    "h6": {"tree": { ...compact json... }},
    "h7": {"console": ["[warn] ...","[error] decrypt: ..."]},
    "h8": {"failures": [{"url":"...","status":404}]},
    "h9": {"axtree": { ...roles... }},
    "a1": {"artefact": {"inline_b64":"...","size_bytes":33801}}
  }
}
```

Now in **one request** I tested three selector hypotheses, counted tabs, read the title,
got a depth-3 DOM map, read the console, saw network failures, got the a11y tree, and took
a screenshot — all against the same page state. My *next* request is fully informed. This
is the difference between debugging in 1 round-trip vs 8.

---

## 3. Why this is the right model for an agent specifically

A human debugging in DevTools has the whole page live in front of them — they glance at the
console, hover the element, type in the console, all against one frozen state, for free. An
agent driving over HTTP pays a full round-trip (and often a full navigate + settle) for
*each* glance. The probe-batch collapses "everything I'd glance at" into one request, which
is exactly how a human actually debugs.

It also matches how I reason: I form **multiple hypotheses at once** ("it's probably
selector A, but maybe B, and if neither then the console will say why"). Forcing me to test
them serially, one round-trip each, throws away the parallelism that's natural to the task.

---

## 4. Server-side techniques that make this cheap and powerful

These are things the server can do *because it has direct Playwright access to the live
Chromium* that I can't do from outside — and that make the probe model fast:

### 4.1 Snapshot once, probe against the snapshot
After settle, the server holds a live page handle. All read-probes execute against that one
handle without re-navigating. The expensive part (launch + navigate + decrypt) happens once;
probes are milliseconds each. **This is the core efficiency win** — amortise the costly
setup across many cheap reads.

### 4.2 Run independent probes concurrently server-side
Playwright can evaluate multiple read-only expressions against one page in parallel. The
server can fan out the probe list, gather results, and return them together. The agent sees
one request; the server did N concurrent reads.

### 4.3 Capture console + network from navigation start
The server can attach `page.on('console')` and `page.on('requestfailed')` **before**
navigation, buffer them, and expose them as probes (`console_tail`, `network_failures`). I
can never get these after the fact from outside — they're emitted during load. This alone
turns most "page is blank, why?" mysteries into a one-probe answer.

### 4.4 Auto-capture on settle-failure
If `settle` times out, the server should *automatically* attach: a screenshot of whatever
state the page reached, the console tail, the network failures, and a shallow DOM tree —
**without me asking**. The failure case is exactly when I'm blind and need the most context.
Today a timeout gives me nothing; it should give me the forensics by default. (This
generalises G2 `screenshot_on_fail` into `diagnostics_on_fail`.)

### 4.5 A "describe this page" macro probe
A single probe type — `type: "page_summary"` — that returns the server's best one-shot map:
title, URL, visible headings, landmark roles, count of interactive elements, any console
errors, any failed requests, and a shallow DOM tree. For an unfamiliar page this is the
"orient me" call. The server can assemble it far more cheaply than me requesting each piece.

### 4.6 Selector resolution with candidates
A probe `type: "resolve"` that takes a *list* of candidate selectors and returns, for each,
`{exists, count, visible, text_sample, rect}`. Purpose-built for "which of my hypotheses is
right?" Returns the answer for all candidates in one pass over the DOM.

### 4.7 Element-scoped DOM tree that pierces shadow/iframe
As in FR-2/FR-3 but emphasised for debug: when I give a `root_selector`, return the compact
tree *including* open shadow roots and same-origin iframes, with boundaries marked. Most of
my "I can't find the element" pain is shadow-DOM encapsulation; a piercing tree ends it.

### 4.8 A bounded JS scratchpad for reads (carefully)
The current `evaluate` allowlist is so strict it only returns constants. For *debug mode*
specifically, consider a **read-only-but-expressive** evaluate: allow arbitrary expressions
but (a) enforce a wall-clock timeout, (b) run in a context where the result is
JSON-serialised and size-capped, (c) keep it strictly within the disposable session (which
it already is). The risk profile is low — it's a throwaway Chromium with no persistent state
and no credentials beyond what I passed for the target page. Letting me run
`[...document.querySelectorAll('[data-section]')].map(e => e.dataset.section)` in one probe
would replace a dozen blind selector guesses. If full expressiveness is too much, a
**curated read library** (`$count(sel)`, `$text(sel)`, `$attrs(sel)`, `$exists(sel)`,
`$sections()`) gives 90% of the value with a tiny, auditable surface.

---

## 5. If I had direct Playwright access, what would I do differently?

Concretely, the things I'd do with a direct `page` handle that the HTTP boundary currently
costs me:

1. **Attach console/network listeners before navigating** — so I never miss load-time
   errors. (→ 4.3)
2. **`await page.waitForFunction(...)`** with an arbitrary predicate instead of guessing a
   selector. (→ FR-1 `function`)
3. **`await page.accessibility.snapshot()`** to orient on an unfamiliar page in one call.
   (→ FR-5 / 4.5)
4. **`page.$$eval(sel, els => ...)`** to extract structured data from many elements at once
   instead of round-tripping per element. (→ 4.8)
5. **Keep the page handle alive** across my reasoning steps so I don't re-navigate +
   re-decrypt for every new question. (→ 4.1; see §6)
6. **`page.locator(sel).all()` + introspection** to test candidate selectors and see what
   each matches before acting. (→ 4.6)
7. **Pierce shadow DOM / frames natively** with Playwright's engines rather than fighting
   CSS selectors. (→ 4.7)

Every one of these is a thing the server *can* do on my behalf and surface as a probe. The
probe-batch model is essentially "give the agent the debugging affordances a direct
`page` handle would, without handing over the handle."

---

## 6. The one stateful ask: an optional short-lived session handle

Everything above is stateless (navigate-and-probe in one request). But the single biggest
cost against an SPA is **navigate + decrypt**, repeated for every request. If the service
offered an **opt-in, short-lived session** —

```
POST /pw/session/open   -> { session_id, expires_in_ms }     # navigate + settle once
POST /pw/session/{id}/probe  -> run a probe batch against the held page
POST /pw/session/{id}/act     -> click/fill/etc, page state persists
POST /pw/session/close
```

— then I could decrypt the vault **once**, then run many probe batches and actions against
that live page across several requests, reasoning between them, and close it when done. This
is the highest-value efficiency change for SPA work: it removes the repeated decrypt cost
entirely. Bound it with a short TTL (the `max_session_lifetime_ms` capability is already in
`/health/info`), one session per token, auto-close on expiry. Stateless probe-batches
(§2) handle the simple cases; the session handles the "I'm going to be here a while
debugging this one page" case.

---

## 7. Priority within this addendum

1. **Probe batch against one settled state** (§2) + **snapshot-once/probe-many** (4.1) —
   the core model. Turns N round-trips into 1.
2. **`diagnostics_on_fail`** (4.4) + **console/network capture** (4.3) — forensics exactly
   when I'm blind.
3. **`resolve` candidate-selector probe** (4.6) + **piercing dom_tree** (4.7) — kill
   selector-guessing.
4. **`page_summary` macro** (4.5) — orient on unfamiliar pages.
5. **Optional session handle** (§6) — removes repeated decrypt cost for sustained SPA work.
6. **Expressive-but-bounded read eval / curated read library** (4.8) — the power tool.

---

## 8. The reframed one-line ask

The original debrief said: *fix `get_content` + add `wait_for: {text|function}`.* This
addendum adds the bigger idea: **make the unit of work "navigate-and-settle once, then run a
batch of independent read-probes against that frozen state, returning all results keyed by
id."** That single change converts the service from a linear action-pipeline into a debugging
instrument — and turns most of my multi-round-trip investigations into one request.

— @Content
