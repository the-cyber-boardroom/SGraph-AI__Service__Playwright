# sg-playwright — Debrief from a Real Driving Session

**from** @Content (Claude session, driving via the vault `/pw` proxy)
**to** the sg-playwright maintainers
**service version observed** v0.2.47 (guide was written for v0.2.45)
**date** 30 May 2026
**context** Used the service to screenshot live library pages on `qa.sgraph.ai` and to
open an encrypted vault SPA on `dev.vault.sgraph.ai`. Real work, not a synthetic test.

---

## TL;DR

The service is genuinely good for static and server-rendered pages — one authenticated
HTTP call per screenshot, no local Playwright, clean inline PNGs. It struggled with
async-decrypting SPAs for one reason: **I had no reliable way to wait for "the thing I
care about" to appear, and no way to read the DOM to discover what to wait for.** Almost
every feature request below is in service of one goal: **never needing a blind `wait`.**

The single most valuable thing you could give me: **a way to wait on a condition
(selector, text, JS predicate, network-quiet) and a way to read the DOM (tree, text,
attributes) so I can discover what to wait on.** With those two, blind waits disappear.

---

## Part 1 — Bugs (reproducible)

### BUG-1 — URL validator rejects `:` in the hash fragment

**Severity:** blocking for any vault-key-in-URL workflow.

**What I tried:**
```json
{"action":"navigate","url":"https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b"}
```

**What I got:** HTTP 400 (request-level, whole sequence rejected):
```
ValueError: in Safe_Str__Url, value does not match required pattern:
^https?://[a-zA-Z0-9.\-]+(:[0-9]{1,5})?(/[...])?(\?[...])?(#[a-zA-Z0-9\-._~%]*)?$
```
The fragment character class `[a-zA-Z0-9\-._~%]` excludes `:`. But `:` is a legal URI
fragment character (RFC 3986 `fragment = *( pchar / "/" / "?" )`, and `pchar` includes
`:`). Our vault keys are `vaultId:accessKey` and live in the fragment.

**Workaround that worked:** URL-encode the colon as `%3A`. The SPA decoded it correctly
and attempted to open the right vault. So this is purely an over-strict validator, not a
real safety boundary.

**Fix:** allow `:` (and ideally `@`, `!`, `$`, `&`, `'`, `(`, `)`, `*`, `+`, `,`, `;`, `=`)
in the fragment class to match RFC 3986 `pchar`. At minimum allow `:`.

### BUG-2 — `get_content` returns empty artefacts / null fields

**Severity:** high — this is what forced me into blind waits (see Part 2).

**What I tried** (after the page had clearly loaded):
```json
{"action":"get_content","content_format":"html","inline_in_response":true}
```
and also `content_format:"text"`, with and without `inline_in_response`.

**What I got:** step `status:"passed"`, but `artefacts: []` and the step's `content` /
`result` fields were both `null`. No DOM came back by any combination I tried.

**Expected:** the page HTML or text, either inline in the step result or as an artefact.

**Why it matters:** without `get_content` I cannot discover the DOM structure of a page I
don't already know. That means I cannot find the right selector to wait on, which forces
blind time-burning waits. This one bug cascades into most of the SPA friction.

---

## Part 2 — The core problem: I had to fake waits

The library pages (server-rendered) were easy. The vault is a client-side SPA that:
1. loads a shell instantly,
2. reads a key from the URL fragment,
3. asynchronously fetches + decrypts vault content,
4. then renders the real UI.

`wait_until:"networkidle"` returns at step 2-3, before the content exists. I needed to
wait for step 4. But:

- I had no `wait` (fixed duration) verb.
- `wait_for` needs a **selector I know in advance** — but I didn't know the post-decrypt
  selectors, and `get_content` (which would let me discover them) was broken (BUG-2).
- So I waited on a deliberately-nonexistent selector (`#burn-18s`) with
  `halt_on_error:false`, letting it time out to burn ~18s, then screenshotted.

That is exactly the anti-pattern your guide tells me to avoid, and I was forced into it.
Everything in Part 3 is about removing that necessity.

---

## Part 3 — Feature requests, ranked by how much they kill blind waits

### FR-1 — `wait_for` on richer conditions (highest value)

Today `wait_for` takes `selector` / `url_pattern` / `state`. Add:

- **`text`** — wait until text appears anywhere (or under an optional `selector` scope).
  `{"action":"wait_for","text":"Decrypted"}` would have solved the vault instantly.
- **`selector_gone`** — wait until a selector *disappears* (e.g. the "Opening vault…"
  spinner). Often more reliable than waiting for the thing that replaces it.
- **`function` / `predicate`** — wait until a JS expression is truthy, evaluated under the
  same allowlist spirit but for booleans:
  `{"action":"wait_for","function":"document.querySelectorAll('article').length > 0"}`.
  This is the universal escape hatch — any "is it ready yet?" becomes expressible.
- **`network_idle_ms`** — "no network requests for N ms", with a configurable quiet window
  (the built-in `networkidle` is 500ms and not tunable; SPAs that poll never reach it).

With `text` + `selector_gone` + `function`, I would essentially never need a blind wait.

### FR-2 — A working DOM read, in three shapes (so I can discover what to wait on)

Fix `get_content` (BUG-2), and offer three explicit read shapes because I want different
granularities at different times:

- **`get_text`** — visible text content of the page or a `selector`. Cheap. Lets me
  confirm "did the content I expect appear?" without parsing HTML.
- **`get_html`** — outerHTML of the page or a `selector`. For when I need structure.
- **`get_dom_tree`** — **this is the one I most want.** A compact JSON tree of the DOM:
  tag name, id, classes, `data-*`, role, accessible name, bounding box, visibility, and
  child count — *without* the text noise of full HTML. Something like:
  ```json
  {"tag":"sg-layout","id":null,"class":"shell","visible":true,
   "rect":{"x":0,"y":0,"w":1280,"h":720},"children":[
     {"tag":"nav","class":"side-nav","child_count":46,"visible":true}, ...]}
  ```
  Give me a `max_depth` and an optional `root_selector`. This single artefact would let me
  understand any unfamiliar page in one call and pick exact selectors — no guessing, no
  waiting blind. This is the highest-leverage *new* artefact you could add.

### FR-3 — iframe / shadow-DOM traversal

Both the infographic tool and the vault use Web Components with **shadow DOM** and some
content lives in iframes. Today selectors don't pierce shadow roots, and I burned a lot of
time in an earlier (local-Playwright) session clicking through shadow DOM by hand.

Requests:
- `get_dom_tree` (FR-2) should **descend into open shadow roots and same-origin iframes**,
  marking the boundary (`"shadow_root":true` / `"iframe":true`) so I understand the
  structure.
- Step verbs (`click`, `fill`, `wait_for`, `screenshot`) should accept a **piercing
  selector syntax** — e.g. Playwright's `>>>` / `:scope` or a `frame` / `shadow_path`
  field on the step — so I can target an element inside a component or iframe directly.
- `screenshot` should accept an `iframe`/`frame_selector` so I can capture just the content
  of an embedded frame (e.g. the rendered vault page inside its container).

### FR-4 — A real `wait` verb (fallback only)

Even with FR-1, a plain `{"action":"wait","ms":1500}` is a reasonable last resort and
removes the `#burn-nonexistent-selector` hack. Low priority *if* FR-1 lands, but trivial to
add and stops people abusing `wait_for` timeouts.

### FR-5 — Artefacts that direct-Playwright can produce and I currently can't get

Things the underlying Playwright can do that would be high-value as artefacts/sinks:

- **`accessibility_tree`** — Playwright's `page.accessibility.snapshot()`. Often a *better*
  map of "what's meaningfully on the page" than the DOM, and much smaller. Great for
  agents reasoning about a page.
- **Computed value of a single expression returned inline** — `evaluate` runs but (per the
  guide) is allowlisted to constant reads and I never saw its return value surfaced cleanly
  in `step_results`. Please return `evaluate`'s result value in the step result (string/
  number/bool/json), not just pass/fail. Half of FR-1's `function` predicate is this.
- **`get_attributes`** — given a selector, return `{tag, id, class, attrs{}, rect, visible,
  text}` for the first (or all) matches. Lighter than full HTML when I just need one thing.
- **Console + network logs as artefacts** (your G3) — when a page renders blank, the
  console error is usually the answer. Today I have to guess. Even a last-N-lines console
  artefact on demand would save whole round-trips.
- **PDF render** of a page (`page.pdf()`) — occasionally nicer than a tall full-page PNG
  for archiving a document-style page.

### FR-6 — Multi-shot capture in one sequence without re-navigation

For documenting a multi-tab/multi-section SPA I want: open once, then
`navigate-to-section → screenshot` repeatedly in **one** sequence sharing the same browser
context (so decryption/auth state persists). Today each `/browser/*` one-shot is a fresh
Chromium, and within `sequence/execute` the context is shared but I can't easily name and
collect N screenshots with labels. A per-screenshot `label` field that flows through to the
artefact (`"label":"section-overview"`) would let me fire one sequence and get back a
labelled set — perfect for "screenshot every section of this doc".

### FR-7 — Return artefact dimensions and let me request a viewport per shot

Minor: artefacts report `size_bytes` but not pixel `width`/`height`. For laying images into
docs I'd love `width`/`height` on the artefact. And `set_viewport` exists as a verb — a
shorthand `viewport` on the `screenshot` step would save a step.

---

## Part 4 — How I'd most like to receive data (summary of preferences)

1. **Inline, in the step result, for small things** (text, a single attribute, an
   evaluate value, a boolean predicate). Don't make me decode an artefact to read a title.
2. **As an inline-base64 artefact for binary** (screenshots) — current behaviour, works well.
3. **As compact JSON, not HTML, for structure** (`get_dom_tree`, accessibility tree). HTML
   is huge and noisy; a structured tree with `max_depth` is what I actually reason over.
4. **With the owning step clearly identified** — current positional inference
   (`step_results[i].artefacts`) is fine, but a `label` (FR-6) would be better.
5. **Errors with the console/network context attached** when a step fails on a blank page.

---

## Part 5 — What already works well (keep it)

- One HTTP call → one screenshot, inline base64. No local browser. This is the whole value.
- Typed per-step results with `error_type` enum — easy to branch on.
- `halt_on_error:false` to continue past expected failures.
- `/pw/sequence/execute` sharing one Chromium context across steps — cheap and correct.
- `x-sgraph-access-token` through the vault proxy — clean auth once you know the header.
- Honest version reporting via `/pw/health/info`.

---

## Part 6 — The one-line ask

If you do nothing else: **fix `get_content` (BUG-2) and add `wait_for: {text|function|
selector_gone}` (FR-1).** Those two together eliminate ~95% of my blind waits and make the
service reliable for the async SPAs that are the whole point of our platform.

— @Content
