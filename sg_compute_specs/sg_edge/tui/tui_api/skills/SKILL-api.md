# SG/Edge local edge — skill (for the agent)

You can operate a **local** SG/Edge edge (a scale-to-zero proxy tier in front of vault
slugs, simulated in-process — no AWS). Use these actions; they map 1:1 to the
`sg edge local *` CLI and call the same backend.

## Read (always safe)
- `status` — is the edge deployed? wildcard, proxy fleet, slug count.
- `slugs` — the registered slugs and their state: `live` (A + backend), `dormant`
  (A only), `orphan_backend` (TXT, no A).
- `check` — deviation findings (missing wildcard/fleet, dormant/orphan slugs).
- `request {slug}` — **simulate** a user request: `200` welcome (live), `503`
  dormant, `404` not recognised. Read-only; the best way to show "how it works".

## Mutate (gated — a human confirms each one)
- `setup` — bring the edge up (zone + wildcard + one proxy). Do this first.
- `register {slug}` — make a slug live (A + backend TXT).
- `register_dormant {slug}` — register A only (no backend yet).
- `unregister {slug}` — remove a slug.
- `teardown` — destroy the whole local edge (DESTRUCTIVE — always confirmed).

## Sequence
The edge must be `setup` before slugs are useful. The golden loop is
**`setup` → `register alice` → `request alice`** → "Welcome to the alice vault".

## Honesty
Mutating actions are **local-only**. On the AWS edge they are not available (the
live-EC2 path is pending) — only the read actions appear. Never claim a slug is live
without a `request` or `slugs` confirming it.
