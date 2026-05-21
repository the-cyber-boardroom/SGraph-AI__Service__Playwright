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
| Bench (Slice 6 local) | `bench/Edge_Bench__Suite` + `bench/scenarios/Edge_Bench__Scenarios` | 8 runnable LOCAL doc-05 scenarios (P-03/07/12, F-01/06/08, X-07/12) over the local edge via `sg edge bench`; 8 aws-bench scenarios registered + skipped |
| TUI data layer | `tui/source/*` + `tui/service/*` + `tui/schemas/*` | shared snapshot seam for the SG/Edge TUI (T1): one normalised `Schema__SG_Edge__TUI__Snapshot` from a local or AWS-DNS source, plus pure `Differ` / `Metrics` / `Comparison` / `Card` |
| TUI screen S1 | `tui/screens/SG_Edge__TUI__Screen__Deployment` + `tui/cli/Cli__SG_Edge__Tui` | `sg edge tui deployment` — Deployment Reality (Textual; gated/lazy; no-TTY → static card) |
| TUI screen S2 | `tui/screens/SG_Edge__TUI__Screen__Topology` | `sg edge tui topology` — layered flow + ↑/↓ slug navigation (no-TTY → static card) |
| TUI screen S3 | `tui/screens/SG_Edge__TUI__Screen__Compare` | `sg edge tui compare` — Local vs Edge drift (reads both sources; no-TTY → plain diff) |
| TUI screen S4 | `tui/screens/SG_Edge__TUI__Screen__Slug_Detail` | `sg edge tui slug [name]` — per-slug deep-dive (State+DNS real; rest pending); Topology `Enter` drills in |
| TUI screen S5 | `tui/screens/SG_Edge__TUI__Screen__Events` | `sg edge tui events` — live state-transition feed + honest sparklines (Differ + Metrics); pause / filter / clear |
| TUI screen Docker | `tui/screens/SG_Edge__TUI__Screen__Docker` | `sg edge tui docker` — local running containers (`docker ps`); also embedded in Deployment |
| TUI dashboard | `tui/screens/SG_Edge__TUI__App` | `sg edge tui dashboard` — all screens in one app, Textual `TabbedContent` (1..6 / ←→ to switch) |
| TUI slugs (DataTable) | `tui/screens/SG_Edge__TUI__Screen__Slugs` + `widgets/SG_Edge__TUI__Table` | `sg edge tui slugs` — slug inventory as a real Textual `DataTable` (built-in cursor/scroll/click; Enter → detail). Prototype of the widget approach vs markup, via a generic Type_Safe→rows helper |
| TUI Control Center | `tui/screens/SG_Edge__TUI__Screen__Control_Center` | `sg edge tui control` — action-capable cockpit on the shared `Tui__App` + Debug Panel: register / request / setup / teardown (capability-gated, confirm on destructive). Each action = one `sg edge local *` backend call |

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
sg edge tui topology                    # Screen 2 — layered flow (↑/↓ select; Enter → detail)
sg edge tui compare                     # Screen 3 — local vs edge drift (reads both)
sg edge tui slug alice                  # Screen 4 — per-slug deep-dive (↑/↓ to switch)
sg edge tui events                      # Screen 5 — live event feed + sparklines
sg edge tui docker                      # local running containers (docker ps)
sg edge tui dashboard                   # ALL screens in one app — tabbed nav (1..6 / ←→)
```

**All five exploratory screens exist.** S2 (`…Screen__Topology`) draws the layered
browser → wildcard → fleet → slugs flow (↑/↓; `Enter` drills into S4). S3
(`…Screen__Compare`) renders local-vs-edge drift via the `Comparison` service. S4
(`…Screen__Slug_Detail`) deep-dives one slug (STATE + DNS + backend real; the rest
labelled pending). S5 (`…Screen__Events`) polls and diffs successive snapshots via
the `Differ`, streaming honest state-transition events with `Metrics`-backed
sparklines (counts the TUI measured — not rps); pause / filter / clear.

Every screen shares `q` quit · `?` context-aware help overlay · `t` dark/light
theme · `e` export the snapshot as an ASCII card to the clipboard (OSC-52).
`sg edge tui diagnose` prints terminal capability checks ($TERM/$LANG/colors/unicode/
truecolor) for the SSH/SSM + `docker exec` chain. Full operator guide:
[`library/guides/v0.2.38__sg-edge-tui-guide.md`](../../library/guides/v0.2.38__sg-edge-tui-guide.md).

Textual is a lazy/gated dependency: registering `sg edge tui` never imports it, and
each screen falls back to static output when stdout is not a terminal. All five
screens + the T-chain polish are done; what remains is the **sixth conversation** —
which screens get promoted into a canonical composite `sg edge tui` app.

## Not built yet (deferred — see plans)

- **EC2 launcher/terminator** wiring the reconciler's `_launcher`/`_terminator`
  seams; **`Setup__*`** provisioning (ACM/IAM/Lambda/CF/DNS) — live-AWS, Slice 5.
- **`sg edge setup *`** + live `boot`/`reconcile`/`drain`/`waker logs` — Slice 5 (CLI-2).
- **Bench aws-bench target** — the 8 AWS-timing scenarios (P-01/05/06/10/11, X-04/05/10)
  are registered but skipped (`sg edge bench … --target aws-bench` needs the Slice-5/6
  live backend) + the docker-compose OpenResty stack. The 8 LOCAL scenarios run today.

## Running the bench (Slice 6 local)

```bash
sg edge bench list                       # the doc-05 scenario catalog
sg edge bench scenario F-01 --repeat 10  # one scenario → p50/p95/p99 + PASS/WARN/FAIL
sg edge bench primitives                 # a whole tier  (also: flows / failures)
sg edge bench full                       # every scenario (= sg edge_bench full)
#   --target local (default) | aws-bench   --json   --output runs.json
```

Local scenarios run in-process against a temp `sg edge local` stack and gate p95 on
generous code-path budgets (catch gross regressions, no CI flakiness); the brief's
AWS acceptance thresholds apply to `--target aws-bench` (not built). Exit code is
non-zero on any non-skipped FAIL — drop `sg edge bench full` into CI as a no-AWS gate.

## Running the tests

```bash
python3   -m pytest sg_compute_specs/sg_edge/tests/   # 3.11: 104 pass, 68 skip (typer + FastAPI)
python3.12 -m pytest sg_compute_specs/sg_edge/tests/  # 3.12: 172 pass (CLI + bench + FastAPI)
python3.12 -m pytest sg_compute_specs/sg_edge/tui/tests/  # TUI (T1+S1): 3.12 → 32 pass; 3.11 → 27 pass + 5 gated-skip (textual/typer)
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
