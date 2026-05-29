# Playwright Workbench — Dev Pack (sg-playwright service changes)

**Created:** 2026-05-29 · **Owner:** Architect (Claude, Opus 4.8) · **Repo:** `SGraph-AI__Service__Playwright` @ `claude/cool-bell-GLbss` (v0.2.41 line)
**Status:** REVIEW PACK — for human ratification before implementation. No service code changed yet.

This folder is the design pack for the next batch of changes to the **`diniscruz/sg-playwright`** image, prompted by a briefing from the team building the **Playwright Workbench** (a vault-resident QA tool that drives the service over its `/pw/*` REST API).

## Read in this order

| # | File | What it is |
|---|------|-----------|
| 00 | [`00__original-brief__from-workbench-team.md`](00__original-brief__from-workbench-team.md) | The incoming brief, verbatim. |
| 01 | [`01__architecture-and-implementation-review.md`](01__architecture-and-implementation-review.md) | The plan — phased build (sync fixes + new async path + cleanup). ⚠ **Some §1-§2 diagnoses are corrected by `04` — read `04` first.** |
| 02 | [`02__playwright-api-for-agents__v0.2.42__PROPOSED.md`](02__playwright-api-for-agents__v0.2.42__PROPOSED.md) | **Consumer-facing API guide for the *proposed* target state.** Hand this back to the Workbench agent with: *"if we build this, does it do what you need?"* Supersedes `library/guides/v0.2.6__playwright-api-for-agents.md` once built. |
| 03 | [`03__questions-for-the-workbench-agent.md`](03__questions-for-the-workbench-agent.md) | Open questions back to the Workbench team. |
| 04 | [`04__empirical-findings__live-v0.1.162.md`](04__empirical-findings__live-v0.1.162.md) | **GROUND TRUTH.** Live test results against the actual deployed `:latest` (v0.1.162). Falsifies parts of `01` and clarifies the brief. Read before `01`. |

## One-paragraph summary

After live testing against the deployed `:latest` (v0.1.162 — **40+ versions behind HEAD**), the truth is sharper than my first review: **the asyncio crash the brief reported is real and live**, but the brief misidentified the trigger — `screenshot` works fine; **`wait_for`, `press`, `hover`, `scroll` are the verbs that crash with `"sync API inside asyncio loop"`**. Their test sequences happened to include `wait_for` before the screenshot. Implemented verbs that work today: `navigate, click, fill, screenshot, get_content, get_url, evaluate` (+ allowlist). Per-step isolation **works for normal exceptions** (bad selector → step `failed`, sequence continues) but **the asyncio error escapes it entirely** — that's the durable hardening gap. The rich `capture_config` (terminal screenshot, video/har/trace/console) is confirmed **schema-only — not wired at runtime**. Artefact shape is **closer to target than I credited** (just needs `step_index/content_type/encoding/filename` added). Per owner steering: **keep sync + fix it, add parallel async, share orchestration core, quality-first refactor.**
