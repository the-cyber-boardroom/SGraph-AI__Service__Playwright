# 2026-04-25 — `sp el` (Ephemeral Kibana) — 1 / 3 — Why we built this

This is part one of a three-part debrief on the `sp elastic` slice.

| Part | File |
|------|------|
| 1 — **Why we built this** *(this doc)* | `2026-04-25__sp-elastic-kibana__01-why.md` |
| 2 — What we built | `2026-04-25__sp-elastic-kibana__02-what.md` |
| 3 — How to use it | `2026-04-25__sp-elastic-kibana__03-how-to-use.md` |

---

## The problem

We needed a **scratchpad observability stack** for the SGraph ecosystem — somewhere to dump a few thousand synthetic log documents, click around in a real Kibana, demo a dashboard, then throw the whole thing away.

The available paths all had the wrong shape:

| Option | Why it didn't fit |
|---|---|
| **Elastic Cloud** | Permanent, billed monthly, takes a credit card and a contract. Not "spin up for an hour and kill". |
| **AWS OpenSearch Service** | Same — managed, multi-AZ, ~$200/mo minimum, not throwaway. |
| **Existing `sp ob create` (OpenSearch)** | We already had this for the Playwright service's own logs. Works for production observability, but OpenSearch Dashboards is a noticeably weaker dashboard product than Kibana. The viz library, the data-view UX, the "ES|QL" query bar, the dashboard-clone-and-share flow — Kibana wins on every one. |
| **Local Docker Compose** | Fine for one developer on one machine. Doesn't help with reviewer demos / shared sessions / CI smoke tests / multi-region experiments. |

So the gap: an **ephemeral**, **scripted**, **single-command** way to get a real Elasticsearch + real Kibana on a real EC2, then drop it again — with the data + the data view + a working dashboard already there on launch.

## What "ephemeral" actually means

Three properties that drove every design decision:

1. **Cheap to create** — under 3 minutes from `sp el create` to a working Kibana URL.
2. **Cheap to destroy** — `sp el delete --all -y` and you're back to zero.
3. **Cheap to forget** — auto-terminate after 1 hour by default, so a forgotten `sp el create` doesn't bill overnight.

The ~$0.19/h cost on `m6i.xlarge` is a feature: small enough to not care about, big enough to actually run ES + Kibana without OOM-killing.

## Why baked AMIs

The cold path is ~158 seconds (Docker pulls, ES boot, token mint, Kibana plugin init, harden). For a daily "grab a Kibana for an hour" use case, that's the wrong order of magnitude — you want **single-digit-tens-of-seconds** so the cost of starting one is invisible.

The AMI flow gets us to ~80s end-to-end (49% reduction). That number isn't great in absolute terms — it's mostly the EC2 boot itself plus Docker daemon start — but it's at the right level for "just spin one up while I'm getting coffee".

The trade-off the AMI accepts:

| | Cold path | AMI path |
|---|---|---|
| Time | 158s | 80s |
| Password | Random per stack | Same as bake-time (intentional) |
| Data + dashboard | Created at seed time | Already in the snapshot |
| Customisation | Each launch | Frozen at bake time |

## Why "Ephemeral Kibana" branding

The user landed on the name partway through the slice. It captures the value prop:

> **Ephemeral Kibana** — a single-node Elasticsearch + Kibana + nginx-TLS box, designed to live for an hour and die.

It also disambiguates from the "real" Elastic offerings — this isn't a managed service, it isn't HA, it isn't backed up. It's a sketchpad.

## Why this lives under `sp el` and not somewhere else

The CLI is part of the SGraph Playwright service repo because it's used by the same team for the same kind of work (provisioning short-lived AWS resources for testing / demos). The pattern matches the existing `sp create` (Playwright EC2) and `sp ob create` (OpenSearch) commands — same provisioning shape, same `sp el list` / `sp el delete` lifecycle, same SSM-based exec/connect.

## Why we left the password baked into the AMI

Considered, decided against:

- **Rotate-on-first-boot**: detect a sentinel in `.env`, generate a new password, restart containers. ~50 lines. Adds a dependency on `bin/elasticsearch-reset-password` running cleanly in cloud-init, which complicates failure modes.
- **Read from instance user-data**: have user-data write the password before docker comes up. Coupling: the password is now in the EC2 metadata, which is queryable from inside the instance and from any IAM role attached.

**What we shipped instead**: explicit `--password` flag on `sp el create`, with `$SG_ELASTIC_PASSWORD` env-var fallback. The user pins their own strong password once via `export`; every stack and every AMI carries that same password. Simple, predictable, zero magic.

The trade-off: an AMI shared with a third party gives them the bake-time password. For internal use that's a feature. For a public Marketplace listing it would be a problem — see the marketplace section below.

## Why we didn't put it on AWS Marketplace

Two real blockers, both noted in conversation but not addressed in this slice:

1. **Elastic license (ELv2 + SSPL)** — the 8.13.4 docker images are not redistributable as a managed/hosted service. AWS Marketplace counts as redistribution. Elastic NV publishes their own offerings; third-party Marketplace listings of Elasticsearch/Kibana have historically been DMCA'd. Self-hosted use (`git clone` and run yourself) is fine because the user pulls the images directly from Elastic's registry under Elastic's license — we never redistribute them.

2. **Baked password** — Marketplace AMIs are launched by anyone, so a baked secret would ship our password to every customer. Would need rotate-on-first-boot before going public.

The user's conclusion: leave it as open-source code, anyone who wants it can `git clone` and run `sp el create` against their own AWS. Clean separation, no licensing fog.

## What "good" looks like

The slice is "done" when:

- [x] One command goes from nothing to a working Kibana with synthetic data and a dashboard
- [x] One command tears it all down
- [x] One command bakes the current state to an AMI
- [x] One command launches a fresh stack from the AMI in under a minute
- [x] One command surfaces every common failure mode (`sp el health`)
- [x] No manual click-through required after `sp el create --wait --seed`
- [x] AMIs are self-contained — no follow-up CLI calls needed on instances launched from them
- [x] The whole thing is auto-terminate-protected (default 1h)
- [x] Tests cover every service path with no mocks (165 unit tests across the slice)

All boxes checked.

## Open follow-ups

Things considered and explicitly punted, in rough priority order:

1. **OpenSearch fork** — for license cleanliness or Marketplace, swap the Elastic images for OpenSearch + OpenSearch Dashboards. ~50-line user-data change, dashboard ndjson would need a re-export.
2. **Parallel bulk-post during wait** — bulk-post can technically start once ES is ready (~93s) instead of waiting for Kibana ready (~115s). ~7s savings, ~5% of total. Not worth the threading complexity for that small a win.
3. **Cross-stack dashboard copy** — `sp el dashboard copy --from A --to B`. Useful when iterating, but `dashboard export` + `dashboard import` already chain manually.
4. **AMI rotation policy** — `sp el ami delete --older-than 7d` for cost hygiene.
5. **Diagnose the one-time harden-on-boot miss** — user reported pic2 (default nav) on one launch where pic3 (slim nav) was expected. Need the `/var/log/sg-elastic-harden.log` from that specific stack to know if the script ran, errored, or was skipped.

See part 2 ("What we built") for the full inventory and part 3 ("How to use it") for the user-facing recipes.
