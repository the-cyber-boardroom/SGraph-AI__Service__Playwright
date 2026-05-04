# Dev Packs

**Purpose:** Self-contained briefing packs produced for downstream agent sessions (QA, deploy automation, integration targets).

This folder mirrors the pattern used in `SGraph-AI__App__Send/library/sgraph-send/dev_packs/` — each pack is a versioned subdirectory with every document the target session needs to operate without access to the main vault.

## Conventions

- One directory per pack: `{version}__{pack-name}/`
- Each pack contains its own `README.md` with reading order
- Packs are snapshots — do not edit after publish; produce a new versioned pack instead
- Sensitive content (vault keys, share tokens) is **never** committed — briefing packs point to vault share tokens shared out-of-band

## Current Packs

_None yet. The upstream "playwright-dev-pack" (v0.20.55) is mirrored under [`../briefing/`](../briefing/), [`../guides/`](../guides/), [`../docs/`](../docs/), and [`../reference/`](../reference/) rather than kept as a single pack here._
