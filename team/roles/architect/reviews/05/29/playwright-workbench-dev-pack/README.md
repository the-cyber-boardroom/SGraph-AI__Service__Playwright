# Playwright Workbench — Dev Pack (sg-playwright service changes)

**Created:** 2026-05-29 · **Owner:** Architect (Claude, Opus 4.8) · **Repo:** `SGraph-AI__Service__Playwright` @ `claude/cool-bell-GLbss` (v0.2.41 line)
**Status:** REVIEW PACK — for human ratification before implementation. No service code changed yet.

This folder is the design pack for the next batch of changes to the **`diniscruz/sg-playwright`** image, prompted by a briefing from the team building the **Playwright Workbench** (a vault-resident QA tool that drives the service over its `/pw/*` REST API).

## Read in this order

| # | File | What it is |
|---|------|-----------|
| 00 | [`00__original-brief__from-workbench-team.md`](00__original-brief__from-workbench-team.md) | The incoming brief, verbatim. Written by the Workbench agent — accurate on *intent*, partly wrong on *current code state* (see 01). |
| 01 | [`01__architecture-and-implementation-review.md`](01__architecture-and-implementation-review.md) | **The plan.** Each ask checked against the actual code; what's already done, what's misdiagnosed, the real bugs, and a phased implementation plan (sync fixes + new async path + cleanup). |
| 02 | [`02__playwright-api-for-agents__v0.2.42__PROPOSED.md`](02__playwright-api-for-agents__v0.2.42__PROPOSED.md) | **Consumer-facing API guide for the *proposed* target state.** This is the doc to hand back to the Workbench agent with: *"if we build this, does it do what you need?"* Supersedes `library/guides/v0.2.6__playwright-api-for-agents.md` once built. |
| 03 | [`03__questions-for-the-workbench-agent.md`](03__questions-for-the-workbench-agent.md) | Open questions back to the Workbench team — answers shape the build. |

## One-paragraph summary

The brief's headline ask (§2 "screenshot crashes the whole sequence with a sync-Playwright-in-asyncio error") is **partly already fixed in committed code** (an asyncio-loop guard exists) and **partly misdiagnosed**: the real "one step aborts the sequence" cause is that **9 of the 16 step verbs are unimplemented stubs that `raise NotImplementedError`**, and the runner doesn't isolate step exceptions. Per-step error isolation and `halt_on_error` **already exist** for implemented verbs. The rich `capture_config` (video/har/trace/console/terminal-screenshot) is **schema-only — not wired at runtime**. Per the owner's steering we will **keep the sync path (and fix it) and add a parallel async path with maximal shared code**, and treat this as a **quality-first refactor** of critical infrastructure.
