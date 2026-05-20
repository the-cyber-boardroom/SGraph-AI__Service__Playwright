# sg_edge — SG/Edge central edge tier

Scale-to-zero edge in front of vault targets: **CloudFront + wildcard ACM →
OpenResty proxy fleet → vault backends**, coordinated by an **Edge Waker** with
**DNS-as-registry** state and **no coordination service** (convergent
reconciliation, no lock). This package is the SG/Edge spec — a purely additive
sibling to `vault_app` / `vault_publish`.

> Status: **Phase 1 control plane + assets + bench core landed and tested.**
> Live-AWS wiring (EC2 launcher/terminator, `Setup__*`) and the `sg edge` CLI are
> not built yet. See the plans below.

## What exists today

| Area | Class | What it does |
|---|---|---|
| Wire format | `service/SG_Edge__TXT__Builder` | compose/parse `_sg.<slug>` routing TXT (`v=1;ip=…;port=…;type=…;launched=…`) |
| Wire format | `service/SG_Edge__State__Builder` | compose/parse `_state.<parent>` teardown TXT (`zero_streak=N;updated=N`) |
| DNS registry | `service/SG_Edge__DNS__Helper` | over `sg aws dns`: `proxies.<parent>` A membership, `_state` TXT counter, `_sg.*` active-slug read |
| Control loop | `service/SG_Edge__Fleet__Reconciler` | convergent `ensure_booting` / `reconcile` (scale-up) / `idle_check` (teardown); EC2 seams injected |
| Edge Waker | `lambdas/edge_waker/Fast_API__Edge_Waker` + `routes/Routes__Edge_Waker` | `Serverless__Fast_API` Lambda: `/__edge__/health\|status\|reconcile\|idle-check` + cold-cold loading page |
| Proxy rig | `proxy/nginx.conf` + `service/SG_Edge__Proxy__User_Data` | OpenResty: `:80` public static short-circuit + `:8089` VPC-private `/_edge/*` mgmt surface; EC2 cloud-init |
| CloudFront fn | `cloudfront_function/viewer_request.js` + `service/SG_Edge__CloudFront__Function` | viewer-request: preserve Host, extract slug → `X-SG-Host` / `X-SG-Slug` |
| Bench core | `bench/Edge_Bench__Runner` + `Edge_Bench__Stats` | p50/p95/p99 percentiles → PASS/WARN/FAIL verdicts vs doc-05 target/hard_fail thresholds |
| CLI | `cli/Cli__SG_Edge*` | `sg edge` umbrella: `status`, `idle-check`, `dns *`, `proxy *`, `bench`, `waker` (+ `boot`/`reconcile`/`drain` Slice-5 stubs) |
| Local deploy | `local/Local__Edge__Stack` + `Local__Route53__Client` + `Local__Edge__Proxy` | file-backed in-process local edge: setup / register / request / check / teardown — no AWS, no docker |
| TUI data layer | `tui/source/*` + `tui/service/*` + `tui/schemas/*` | shared snapshot seam for the SG/Edge TUI (T1): one normalised `Schema__SG_Edge__TUI__Snapshot` from a local or AWS-DNS source, plus pure `Differ` / `Metrics` / `Comparison` / `Card`. No Textual yet — screens are later slices |

State model (all in DNS, nothing else): `proxies.<parent>` A (fleet membership),
`_state.<parent>` TXT (zero_streak teardown counter), `_sg.<slug>.<parent>` TXT
(routing, read-only here — written by the Vault Waker in Phase 2).

Hard-coded zones: **`edge.sg-labs.app`** is the default AWS edge parent (the
create/destroy-at-will distribution + Route 53 zone); **`edge.sg-labs.local`** is
the local stack's zone. Both in `local/sg_edge_local__config.py`.

## Local deployment — `sg edge local`

A fully in-process local edge (no AWS, no docker) that replicates the end-to-end
flow against a file-backed local DNS server (`<state_dir>/dns.json`, default
`~/.sg/edge_local`, override `$SG_EDGE__LOCAL_STATE_DIR`). The stack plays both
wakers: setup writes `proxies`/`_state` (Edge Waker), `register` writes the
`<slug>` A + `_sg.<slug>` TXT (Vault Waker). The local proxy serves a slug-aware
**"Welcome to the &lt;slug&gt; vault"** page, with the three Phase-2 hot-path
outcomes (welcome / dormant / not-recognised).

```bash
sg edge local setup                    # zone + wildcard + one proxy in the fleet
sg edge local register alice           # A + backend TXT  → "welcome"
sg edge local register bob --no-backend  # A only          → "dormant" (loading page)
sg edge local request alice            # end-to-end → HTTP 200 "Welcome to the alice vault"
sg edge local request ghost            # → HTTP 404 "slug not recognised"
sg edge local check                    # rich ASCII diagnostics + deviation findings
sg edge local serve --port 8410        # real HTTP server (route by Host header)
sg edge local teardown --yes           # destroy local DNS + stack state

sg edge local usecases                 # list scripted end-to-end use-cases
sg edge local usecase UC-02            # run one (UC-01 … UC-06)
sg edge local usecase all              # run them all, one by one
```

`check` draws a layered box diagram (browser → wildcard → proxy fleet → slugs)
with ✓/●/✗ per layer and a Checks panel listing any deviations (orphan backend,
dormant slug, missing wildcard/fleet, records-without-a-stack-marker).

## SG/Edge TUI — `tui/` (data layer landed; screens pending)

A visually-rich Textual TUI is planned (see `team/comms/plans/v0.2.38__sg-edge-tui/`).
**Slice T1 — the shared data layer — exists today** and is pure (no Textual, runs
on 3.11):

- `tui/schemas/Schema__SG_Edge__TUI__Snapshot` — one normalised, source-independent
  snapshot (zone / wildcard / fleet / slug-state / issues / `capabilities`).
- `tui/source/SG_Edge__TUI__{Local,AWS}_Source` over `SG_Edge__TUI__Data_Source` —
  Local wraps `Local__Edge__Stack`; AWS reads the live `edge.sg-labs.app` DNS
  registry read-only (mutations raise until Slice 5; `can_act()` is False).
- `tui/service/` — `Snapshot__Builder` (shared by both sources), `Differ`
  (state-transition events), `Metrics` (honest sparkline ring buffers), `Comparison`
  (local-vs-edge), `Card` (ASCII export). All pure.

`capabilities` makes "no data yet" first-class: cost / throughput / instance panes
are deliberately absent (pending Slice 5), never fabricated.

**Slice S1 — the Deployment Reality screen — also exists today**: a Textual app
(`tui/screens/SG_Edge__TUI__Screen__Deployment`) showing edge infrastructure /
proxy fleet / slugs / checks at a glance, with a pure render module
(`…Deployment__Render`, testable on 3.11) and shared glyph helpers. Run it via:

```bash
sg edge tui deployment                 # local edge (Textual; q quit, r refresh)
sg edge tui deployment --target aws     # live edge.sg-labs.app DNS (read-only)
sg edge tui deployment | cat            # no TTY → static ASCII card fallback
```

Textual is a lazy/gated dependency: registering `sg edge tui` never imports it, and
the screen falls back to a static card when stdout is not a terminal. The remaining
screens (S2 Topology, S3 Compare, S4 Slug detail, S5 Events) are later slices.

## Not built yet (deferred — see plans)

- **EC2 launcher/terminator** wiring the reconciler's `_launcher`/`_terminator`
  seams; **`Setup__*`** provisioning (ACM/IAM/Lambda/CF/DNS) — live-AWS, Slice 5.
- **`sg edge setup *`** + live `boot`/`reconcile`/`drain`/`waker logs` — Slice 5 (CLI-2).
- **`sg edge bench` scenarios** (P-*/F-*/X-*) + docker-compose OpenResty stack — Slice 6.
  (The `sg edge local` stack above is the pure-Python equivalent for the dev loop.)

## Running the tests

```bash
python3   -m pytest sg_compute_specs/sg_edge/tests/   # 3.11: 94 pass, 63 skip (typer + FastAPI)
python3.12 -m pytest sg_compute_specs/sg_edge/tests/  # 3.12: 157 pass (CLI + FastAPI included)
python3   -m pytest sg_compute_specs/sg_edge/tui/tests/  # TUI data layer (T1): 22 pass — pure, runs on 3.11
```

The CLI tests need `typer`, and the `test_Fast_API__Edge_Waker` tests need
`osbot-fast-api-serverless` (Python ≥3.12) + `httpx`; both `@skipUnless` cleanly
on 3.11 (where neither is installed). The local-stack tests
(`test_Local__Edge__Stack`) are pure Python and run on 3.11 too. No mocks, no
patches — AWS-touching tests use `Route53__AWS__Client__In_Memory`; the local
stack uses the file-backed `Local__Route53__Client`.

## Plans & history

- Implementation plan: `../../team/comms/plans/v0.2.37__sg-edge/README.md`
- CLI plan: `../../team/comms/plans/v0.2.37__sg-edge/sg-edge-cli-plan.md`
- Briefs: `../../team/humans/dinis_cruz/briefs/05/20/sg-edge/`
- Debriefs: `../../team/claude/debriefs/` (search `sg-edge`)
