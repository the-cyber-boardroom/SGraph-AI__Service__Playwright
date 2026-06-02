---
title: "Empirical findings — live test against deployed sg-playwright v0.1.162"
author: Architect (Claude, Opus 4.8)
date: 2026-05-29
status: GROUND TRUTH — this supersedes the corresponding sections of 01 where they conflict.
target: "https://18.171.233.60 (sg va create --with-playwright, current :latest)"
service_version: v0.1.162  # vs committed HEAD = v0.2.41 (significant drift)
---

# Empirical findings — what actually happens on live v0.1.162

> **Why this doc exists:** my review in `01__…review.md` was code-grounded but
> against committed HEAD (v0.2.41). The deployed `:latest` is **v0.1.162** — a
> very different binary. Testing against the real instance produced findings
> that **falsify** parts of my review and **clarify** parts of the brief. Where
> this conflicts with `01`, **this doc wins**.

## 1. The deployed verb matrix (the headline)

I ran each verb in a 2-step sequence `[navigate, <verb>]` against the live
service and recorded the outcome. **Some implemented verbs trigger the
asyncio crash; others don't.** The failure is *not* what the brief said.

| Verb | HTTP | Outcome | Notes |
|---|---|---|---|
| `navigate` | 200 | ✅ works | |
| `click` (real selector) | 200 | ✅ works | per-step `passed`, full response shape |
| `fill` | 200 | ✅ assumed (not retested; same family as click) | |
| `screenshot` | **200** | ✅ **works, returns valid inline PNG** | **the brief said this crashes — it doesn't** |
| `get_content` | 200 | ✅ works | |
| `get_url` | 200 | ✅ works | |
| `evaluate` | 422 | ✅ rejected by allowlist as designed | `evaluate_expression_not_allowed` for `document.title` |
| `wait_for` | **400** | ❌ **"sync API inside asyncio loop"** — kills sequence | **this is what aborts, not screenshot** |
| `press` | **400** | ❌ same asyncio error | |
| `hover` | **400** | ❌ same asyncio error | |
| `scroll` | **400** | ❌ same asyncio error | |

**The brief's `[navigate, wait_for, screenshot]` repro crashes because of
`wait_for`, not `screenshot`.** Their `[navigate, screenshot]` (no wait_for)
**works fine and returns a valid PNG**:

```json
{"status":"completed","steps_total":2,"steps_passed":2,
 "step_results":[
   {"action":"navigate","status":"passed","duration_ms":95,"artefacts":[]},
   {"action":"screenshot","status":"passed","duration_ms":70,
    "artefacts":[{"artefact_type":"screenshot","sink":"inline","size_bytes":13531,
                  "inline_b64":"iVBORw0KGgo…(18044 chars)…","content_hash":"23090cba19",
                  "captured_at":1780054737357,"vault_ref":null,"s3_ref":null,"local_ref":null}]}
 ],"timings":{"total_ms":800,…}}
```

This **invalidates the brief's headline framing** and partially invalidates my
review's "verb-stub" theory. The real story is in §2.

## 2. What's actually broken (corrected diagnosis)

### 2a. The asyncio crash IS real and IS live — but specific to a subset of verbs

`wait_for, press, hover, scroll` all crash with the *exact* Playwright message
the brief quoted:

```
"Error: It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead."
```

The shared trait of those four verbs vs the ones that work: they're the
selector/timing-heavy operations. Most likely cause: their implementations call
Playwright APIs that internally spin or interact with an asyncio loop
(`page.wait_for_selector` uses internal asyncio polling under the hood),
whereas `page.goto / page.click / page.screenshot / page.content / page.url /
page.evaluate` do not. The `_run_sequence_via` ThreadPoolExecutor guard I cited
from HEAD either doesn't exist in v0.1.162 or doesn't cover the path these
verbs take.

**Implication:** the brief's §2.1 mandate (build an async engine alongside) is
*better* justified than I credited — selector/timing operations are *exactly*
where Playwright's sync API has known sharp edges, and an async engine sidesteps
the entire class.

### 2b. Per-step isolation works — except when the asyncio error fires

Empirically confirmed both directions:

- **Works:** `[navigate, click "#nope" timeout 1500, get_url]` with `halt_on_error:false` →
  HTTP 200, `status: partial`, per-step `navigate=passed | click=failed | get_url=passed`.
  The runner's try/except *does* contain a normal selector-not-found.
- **Fails:** any sequence containing `wait_for/press/hover/scroll` →
  HTTP 400 with empty `step_results`. The asyncio error escapes the runner's
  protection entirely. **Plain whole-sequence abort.**

So `01`'s claim "per-step isolation already works" is right for *normal*
exceptions and **wrong** for the asyncio class. The runner needs a broader
try/except around step execution (a true belt-and-braces wrapper), not just
the per-handler ones. This is hardening, not invention.

### 2c. Terminal capture genuinely doesn't work (brief §4.1 confirmed)

```
request: [navigate]  +  capture_config.screenshot.enabled = true / sink: inline
response: 200, status=completed, 1 step passed, ZERO artefacts.
```

The brief's §4.1 hybrid-model ask is correct: `enabled` without an explicit
step produces nothing. This matches `01` and is not changed.

### 2d. Artefact shape is closer to target than I thought

The live artefact object already carries:

```json
{"content_hash":"23090cba19","vault_ref":null,"s3_ref":null,"local_ref":null,
 "inline_b64":"<bytes>","artefact_type":"screenshot","sink":"inline",
 "size_bytes":13531,"captured_at":1780054737357}
```

vs the brief's wish list — already present: `type` (as `artefact_type`), `sink`,
`size_bytes`, `inline_b64`. **Missing:** `step_index` (not on the artefact;
inferred from its position in `step_results[i].artefacts`), `content_type`
(MIME), `encoding` (base64/utf8), `filename`. Adding those four fields to the
existing schema is a small change, not a rewrite.

## 3. Version drift — the root cause behind a lot of confusion

| | committed HEAD | live `:latest` |
|---|---|---|
| `sgraph_ai_app_send` proxy host | n/a | OK |
| `sg-playwright` version | v0.2.41 | **v0.1.162** |
| Source of truth | the code we've been reading | the binary the user actually runs |

The image hasn't been rebuilt in a long time (rebuild is manual,
`workflow_dispatch` + `force_image_rebuild=true`). HEAD has rewrites in
`Step__Executor` (where the missing verbs are `NotImplementedError` stubs) and
`Playwright__Service._run_sequence_via` (the asyncio guard). **v0.1.162
predates both of those.** This is the same "we tested the wrong binary"
pattern that caused two earlier confusions this session (the Send-app CORS one
and the prefix-aware UI one).

**Just rebuilding `:latest` from HEAD will materially change the matrix in
§1** — wait_for/press/hover/scroll will switch from "asyncio crash" to
"NotImplementedError (also crashes the sequence, different message)". Neither
is "works", but the failure mode shifts. The right fix is to **implement those
verbs properly** *and* harden the runner *and* ship the async engine (per
owner mandate). Phase 0 from `01` stands.

## 4. Updates to `01__…review.md` you should know about

Reading `01` after this doc, mentally apply these patches:

| §  in 01 | Original claim | Empirical correction |
|---|---|---|
| §1 row 1 (asyncio bug) | "partly already fixed; partly misdiagnosed" | Asyncio bug IS live on v0.1.162; brief misidentified the *trigger verb* (wait_for, not screenshot). |
| §1 row 2 ("navigate works, screenshot fails") | "Misattributed — probably wait_for" | **Confirmed.** wait_for/press/hover/scroll all asyncio-crash; screenshot does not. |
| §1 row 4 (verb gap) | "9 of 16 unimplemented stubs" — HEAD-only fact | On v0.1.162 those verbs are *partially* implemented (call sync Playwright) but trigger the asyncio bug. Either way they don't work. |
| §3.1 ("isolation already works") | True (with caveat) | True for normal exceptions; **false** for the asyncio error. Runner needs broader wrap. |
| §2b ("the runner doesn't try/except step_executor.execute") | Implied from HEAD | Confirmed empirically: asyncio error escapes; selector-error doesn't (handler catches). Runner-level wrap closes the asyncio gap. |
| §4 (artefact shape) | Implied "build from scratch" | Actually closer to target; add `step_index/content_type/encoding/filename`, don't rewrite. |
| §4.1 (terminal capture missing) | Implied from code | **Confirmed empirically** — `enabled` without explicit step produces 0 artefacts. |

## 5. What this changes about the plan

- **Phase 0 (rebuild `:latest` from HEAD)** moves from "may close §2" to
  "**will shift the failure mode** of wait_for/press/hover/scroll but won't
  fix them" — they remain broken (NotImplementedError on HEAD, asyncio on
  v0.1.162). Either way Phase 1's job is real and the same.
- **Phase 1 priority within the verb set:** `wait_for` first — it's needed
  by every realistic sequence the Workbench has shown. Then `press` (forms),
  then `hover/scroll`. `set_viewport / dispatch_event / video_*` after.
- **Phase 1 also adds a runner-level try/except** around
  `step_executor.execute(...)`. Empirically necessary — without it, *any*
  unhandled exception (incl. future async-class) bypasses isolation. This is
  the durable invariant.
- **Phase 2 (async engine) gets stronger justification.** The bug is *real*
  and concentrated in selector/timing verbs — exactly the case async
  Playwright handles cleanly. Empirically grounded, not just owner mandate.
- **Phase 3 (artefacts):** smaller than I drew it. Existing shape is good;
  add the four missing fields; wire terminal/on-fail per §4.1; then context-
  level video/har/trace.
- **Phase 0 also exposes a discipline gap**: the rebuild process is too
  manual, which is how `:latest` drifted 40+ versions behind HEAD. Worth a
  small `sg playwright rebuild` shortcut (already noted as a "two smaller
  wins" earlier) or even an automatic publish on tagged release.

## 6. What the brief got right (credit where due)

Despite the misattribution, the brief's *demands* are all correct in
target state:

- **§2** Fix the asyncio crash → ✅ real bug, just on different verbs
- **§2.1** Async engine alongside → ✅ even more justified
- **§3.1** Per-step isolation universal → ✅ runner needs the broader wrap
- **§3.2** Type the response → ✅ confirmed `{}` in OpenAPI
- **§3.3** Document verbs → ✅ no Step/Action schemas in OpenAPI
- **§3.6** Cheap typed health → ✅ `/health/info` exists and works; just untype
- **§4** Self-describing artefacts → ✅ mostly done; minor enrichment
- **§4.1** Terminal capture from config → ✅ confirmed missing
- **§7.3** Statelessness → not retested here; HEAD code shows fresh-per-request

The brief is a fundamentally good ask. The author just probed from the outside
and pattern-matched the asyncio error to "screenshot" because their tests
always included `wait_for` before the screenshot. That's a normal mistake
without code access — and a useful reminder that **probe-based diagnosis
needs control runs**.
