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
| [`v0.3.0__sg-aws-lab-harness/`](v0.3.0__sg-aws-lab-harness/) | v0.3.0 (post-v2) | PROPOSED | `sg aws lab` measurement harness. 5-Sonnet-sub-agent orchestration plan; sequential after v2 vault-publish phases 2a/2b which ship the `sg aws cf` / `sg aws lambda` primitive expansions. (Renamed from rev-1 `v0.2.28__` which collided with the credentials slot.) |

_The upstream "playwright-dev-pack" (v0.20.55) is mirrored under [`../briefing/`](../briefing/), [`../guides/`](../guides/), [`../docs/`](../docs/), and [`../reference/`](../reference/) rather than kept as a single pack here._
