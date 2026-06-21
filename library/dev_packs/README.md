# Dev Packs

**Purpose:** Self-contained briefing packs produced for downstream agent sessions (QA, deploy automation, integration targets).

This folder mirrors the pattern used in `SGraph-AI__App__Send/library/sgraph-send/dev_packs/` — each pack is a versioned subdirectory with every document the target session needs to operate without access to the main vault.

## Conventions

- One directory per pack: `{version}__{pack-name}/`
- Each pack contains its own `README.md` with reading order
- Packs are snapshots — do not edit after publish; produce a new versioned pack instead
- Sensitive content (vault keys, share tokens) is **never** committed — briefing packs point to vault share tokens shared out-of-band

## Current Packs

| Pack | Version | Status | What it covers |
|------|---------|--------|----------------|
| [`v0.2.8__sg-image-builder/`](v0.2.8__sg-image-builder/) | v0.2.8 | — | Image-builder pack |
| [`v0.2.9__improve-playwritght-api/`](v0.2.9__improve-playwritght-api/) | v0.2.9 | — | Playwright API improvements |
| [`v0.2.11__vault-publish/`](v0.2.11__vault-publish/) | v0.2.11 | PROPOSED | The v2 vault-publish brief — wildcard CF + waker Lambda + per-slug EC2 |
| [`v0.3.0__sg-aws-lab-harness/`](v0.3.0__sg-aws-lab-harness/) | v0.3.0 (post-v2) | PROPOSED (rev 3) | `sg aws lab` measurement harness. 5-Sonnet-sub-agent orchestration plan. Sequential after v2 vault-publish phases 2a/2b. Heavy reuse of v0.2.29's `_shared/` scaffold + `sg aws creds` + `sg aws observe` (Decisions #9, #10). DNS Agent A reuse table refined after code-level deep-dive of `sg aws dns`. |
| [`v0.2.64__playwright-test-pages-and-workflows/`](v0.2.64__playwright-test-pages-and-workflows/) | v0.2.64 | PROPOSED (rev 3) | Rebuild the `GET /` "Try it out" test page into a capability-driven console (built on the shared `sg-layout` + `sg-tool-api` components) exposing the full 21-endpoint / 24-verb surface; portable-JSON workflows matching `/sequence/execute`; in-app docs from `/health/capabilities`; agentic `window.__tool` JS API via the real `sg-tool-api`; root_path-aware asset/component URLs so the console works behind the `/pw` proxy and at root; no-mocks integration tests + Docker image checks that gate the Docker Hub publish. 7-phase multi-agent plan + brief 08 (proxy/components). Design only — no `INDEX_HTML`/runtime changes. |

_The upstream "playwright-dev-pack" (v0.20.55) is mirrored under [`../briefing/`](../briefing/), [`../guides/`](../guides/), [`../docs/`](../docs/), and [`../reference/`](../reference/) rather than kept as a single pack here._
