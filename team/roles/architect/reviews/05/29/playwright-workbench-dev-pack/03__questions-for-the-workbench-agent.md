---
title: "Questions for the Playwright Workbench team (and the owner)"
author: Architect (Claude, Opus 4.8)
date: 2026-05-29
status: OPEN — answers shape the build (dev-pack 01).
---

# Questions back to the Workbench team

These come from checking the brief against the actual service code. Answers change what we build.

## A. Ground-truth / repro

1. **Which exact image/version did you test?** The committed code already has an asyncio-loop guard
   (`_run_sequence_via` → ThreadPoolExecutor), so the *"sync API inside asyncio loop"* error suggests
   you hit an **older deployed `:latest`**. Can you re-run your §2 repro and paste the **full**
   `{"detail": …}` and the `trace_id`? We need to know if it's the asyncio error or an
   unimplemented-verb error.
2. **Did your failing repros always include `wait_for`?** All three of your §5.2/5.3/5.4 examples use
   `wait_for` (or `press`), which are **currently unimplemented stubs that abort the sequence**. We
   suspect that — not `screenshot` — is what aborted your runs. Can you test a sequence of
   **only** `[navigate, screenshot]` (no `wait_for`) and report the result?

## B. Capture semantics (the §4.1 decision)

3. We propose the **hybrid** model: explicit `screenshot` step = mid-run capture; `screenshot.enabled`
   = terminal capture (`step_index:null`); `screenshot_on_fail.enabled` = terminal-on-failure. Does
   that match your mental model and your UI's rendering (per-step vs terminal thumbnails)?
4. For a sequence with **multiple** `screenshot` steps **and** `screenshot.enabled`, you'll get N
   per-step artefacts **plus** one terminal. Is that the desired count, or should `enabled` suppress
   the terminal when explicit steps exist?

## C. Artefact rendering

5. Is the artefact object in 02 §6 directly renderable by your inline viewer, or do you need a
   specific field name/shape (e.g. a single `data` field rather than `inline_b64`)? We can match
   whatever your `<img>`/`<video>` binding expects.
6. For **vault** sink: you said runs already persist to the vault. Do you want the service to write
   the artefact to *your* vault namespace, or return a `vault_ref` you then fetch and re-store? (This
   affects whether the service needs your vault write credentials per request.)

## D. Error typing

7. Is `status:"failed"` + free-text `error_message` enough, or do you want a structured
   `error_type` enum (`timeout | selector_not_found | navigation_failed | evaluate_rejected | …`)
   so the Runner can branch on failure class? (Cheap to add now if you want it.)

## E. Engine choice & sequencing

8. **Do you need the async engine on day one**, or is a *correct sync path* (verbs implemented,
   isolation hardened) enough to unblock you while we build async in parallel? This decides whether
   P1 or P2 ships first.
9. The `engine` marker — do you want it **echoed from a request field** (you choose per call) or just
   **reported** (we tell you which ran)? Or both (`requested_engine` vs `engine`)?

## F. Verb set priorities

10. Beyond `wait_for` (clearly P1), rank the other missing verbs for your near-term workflows:
    `press, select, hover, scroll, set_viewport, dispatch_event`. Which do your §5 examples actually
    need first?
11. Native **assertion verbs** (§7.2) — give us the top 3 you'd use most (`expect_selector_visible`,
    `expect_title_contains`, `expect_url_matches`, `expect_text`, `expect_status`) so we build those
    first.

## G. Idempotency vs statelessness (a real tension)

12. Your §7.8 idempotent `sequence_id` requires the service to **remember** prior results — which
    conflicts with the strict statelessness you (rightly) demand in §7.3. How do you want to resolve
    this? Options: (a) drop idempotency; (b) a short TTL result cache that's explicitly *not* browser
    state; (c) idempotency handled in *your* client/vault, not the service. Our lean: (c).

## H. Screencast / CDP (§7.11/7.12)

13. These are a different surface (websocket relay + lease lifecycle) and fit the **visible-browser**
    specs (`vnc`/`firefox`) better than this stateless headless service. Are you open to that living
    as a *separate* endpoint/spec you point at when you need a live view, rather than inside
    `/sequence/execute`?

---

# Questions for the owner (Dinis)

- **Phasing:** OK that **P1 (implement verbs + harden runner)** ships before **P2 (async engine)**?
  The verbs are the actual blocker; async is the mandate but not what's stopping the Workbench today.
- **Async one-shots:** async variants of `/browser/*` and `/screenshot` too, or just
  `/sequence/execute-async` for now?
- **Screencast/CDP:** separate spec spike (my recommendation) or in-scope for this batch?
- **CI regression suite (brief §6):** stand it up in this repo and gate `:latest` publication on it?
  (Strongly recommend — it's the "trust new versions on sight" guarantee.)
- **Guide publication:** should `02__…__PROPOSED.md` replace `library/guides/v0.2.6__playwright-api-for-agents.md`
  now (labelled PROPOSED), or only once the work lands? (I kept the live guide untouched per the
  reality-doc rule.)
