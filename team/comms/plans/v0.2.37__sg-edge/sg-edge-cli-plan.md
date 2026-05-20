---
title: "SG/Edge — `sg edge` CLI plan (expose the whole edge tier)"
version: v0.2.37
date: 2026-05-20
status: plan / proposed
role: Dev / Architect
audience: implementing engineer (or next Claude thread) building the `sg edge` CLI
related:
  - team/comms/plans/v0.2.37__sg-edge/README.md          # the SG/Edge implementation plan
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__05-mvp-test-and-acceptance.md  # `sg edge_bench`
prior:
  - sg_compute/cli/Cli__SG.py                            # top-level `sg` typer aggregator
  - sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py   # `sg vp` — the closest analogue
  - sg_compute_specs/vault_publish/setup/cli/Cli__Setup.py     # `sg vp setup` — the setup sub-app pattern
  - sg_compute_specs/vault_publish/lambdas/waker/cli/Cli__Waker.py  # `sg vp waker` — the waker sub-app pattern
---

# Why this plan exists

SG/Edge has a control plane (the convergent reconciler), a DNS-as-registry state
model, a proxy rig, a CloudFront viewer function, an Edge Waker FastAPI Lambda,
and a bench measurement engine — but **none of it is reachable from the `sg`
CLI**. Today it is exercised only through pytest and (for the waker) the FastAPI
routes. The owner's directive: *"we should be able to access all the logic and
capabilities of SG/Edge from `sg edge`."*

This plan defines a `sg edge` command surface that exposes every SG/Edge
capability, mirroring the proven `sg vp` (vault-publish) shape exactly. The Edge
Waker already mirrors the vault-publish waker; the CLI should mirror its CLI.

# The one intended touch to existing code

Everything SG/Edge has shipped so far is **purely additive** — nothing outside
`sg_compute_specs/sg_edge/` imports it. Wiring a CLI changes that by exactly
**one line** in `sg_compute/cli/Cli__SG.py`:

```python
# ── edge ───────────────────────────────────────────────────────────────────
from sg_compute_specs.sg_edge.cli.Cli__SG_Edge import app as _sg_edge_app
app.add_typer(_sg_edge_app, name='edge', help='SG/Edge — central edge tier (proxy fleet + Edge Waker).')
app.add_typer(_sg_edge_app, name='ed',   hidden=True)                 # short alias
app.add_typer(_bench_app,   name='edge_bench', hidden=True)           # brief-05 alias → `sg edge bench`
```

This is the same registration every other spec uses (`va`, `vp`, `aws`, …). It
is additive (a new sub-typer, lazy imports inside command bodies) and **changes
no existing command's behaviour**. The zero-impact rule still holds for every
`sg *` command other than the new `sg edge`/`sg ed`/`sg edge_bench` namespaces.
Verify at commit with the same import-graph + CLI-registration greps used so far.

# Command surface

`sg edge` is the umbrella; `bench`, `waker`, and `setup` are `add_typer` sub-apps
(exactly as `sg vp` nests `setup` and `waker`). The brief's documented
`sg edge_bench <scenario>` is preserved as a top-level alias onto `sg edge bench`.

```
sg edge
  status                 fleet snapshot — proxy count, active slugs, zero_streak, desired target
  boot                   cold-cold: ensure one proxy is booting if the fleet is empty
  reconcile              convergent scale check — scale UP toward the target proxy count
  idle-check             idle-teardown counter step — increment / reset / drain
  drain                  force teardown of the whole fleet (remove all proxy A records + terminate)

  dns                    DNS-as-registry diagnostics (read-only; `dig`-equivalent)
    proxies              list proxies.<parent> A values (the fleet IPs)
    state                show _state.<parent> TXT (zero_streak;updated)
    slugs                list active _sg.<slug>.<parent> routing records
    routing <slug>       parse and print one _sg.<slug> TXT record

  proxy                  proxy-asset helpers (pure, no AWS)
    user-data            render the EC2 cloud-init user-data (--version)
    nginx-conf           print the bundled OpenResty config
    cf-function          print the CloudFront viewer-request JS

  bench   (= sg edge_bench)   doc-05 measurement harness
    <scenario>           run one scenario id (P-01, F-01, X-05, …)
    primitives|flows|failures|full
    --repeat N --target local|aws-bench --region R --output FILE

  waker                  inspect / debug the Edge Waker (mirrors `sg vp waker`)
    status               GET /__edge__/status (local app or live Fn URL)
    invoke <route>       invoke a waker route (health|status|reconcile|idle-check)
    logs                 tail the Edge Waker Lambda log group           (live AWS)

  setup                  shared AWS resource provisioning (mirrors `sg vp setup`)
    check                check all areas (iam+lambda+cf+cf-function+acm+dns)
    create|update|delete all areas in dependency / reverse order
    acm                  wildcard *.<parent> ACM cert
    iam                  Edge Waker role + proxy instance role (minimal — brief 02)
    lambda               deploy Edge Waker + Function URL (via `sg aws lambda`)
    cf                   distribution + origin group (primary proxies / secondary waker) + viewer fn
    dns                  bootstrap proxies.<parent> + _state.<parent> records
```

# Capability → command → backing class → status

Every SG/Edge capability that exists today maps to a command. "Now" = works
against the in-memory DNS fake / live Route 53 read path / pure assets with no
new code beyond the CLI shim. "Slice 5" = needs the live EC2 launcher/terminator
or the `Setup__*` classes (not yet built).

| Capability | Command | Backing class (exists) | Lands |
|---|---|---|---|
| Fleet snapshot | `sg edge status` | `SG_Edge__DNS__Helper` + `SG_Edge__Fleet__Reconciler.desired_target` | **now** |
| List fleet IPs | `sg edge dns proxies` | `SG_Edge__DNS__Helper.list_proxy_ips` | **now** |
| Teardown counter | `sg edge dns state` | `SG_Edge__DNS__Helper.read_state` | **now** |
| Active slugs | `sg edge dns slugs` | `SG_Edge__DNS__Helper.list_active_slugs` | **now** |
| Parse routing TXT | `sg edge dns routing <slug>` | `SG_Edge__DNS__Helper.read_routing` + `SG_Edge__TXT__Builder` | **now** |
| Render user-data | `sg edge proxy user-data` | `SG_Edge__Proxy__User_Data.render` | **now** |
| Show nginx conf | `sg edge proxy nginx-conf` | `SG_Edge__Proxy__User_Data.nginx_conf` | **now** |
| Show CF function | `sg edge proxy cf-function` | `SG_Edge__CloudFront__Function.source` | **now** |
| Idle-check step | `sg edge idle-check` | `SG_Edge__Fleet__Reconciler.idle_check` | **now** (increment/reset); drain needs terminator |
| Bench scenario | `sg edge bench <id>` | `Edge_Bench__Runner` / `Edge_Bench__Stats` | **now** (core); live scenario bodies are Slice 6 |
| Waker status/invoke (local) | `sg edge waker status\|invoke` | `Fast_API__Edge_Waker` + `Routes__Edge_Waker` | **now** (py3.12) |
| Cold-cold boot | `sg edge boot` | `SG_Edge__Fleet__Reconciler.ensure_booting` + `_launcher` | **Slice 5** (EC2 launcher) |
| Scale-up | `sg edge reconcile` | `SG_Edge__Fleet__Reconciler.reconcile` + `_launcher` | **Slice 5** |
| Drain fleet | `sg edge drain` | `SG_Edge__Fleet__Reconciler._drain_all` + `_terminator` | **Slice 5** (EC2 terminator) |
| Waker logs | `sg edge waker logs` | `sg aws logs` client | **Slice 5** (deployed Lambda) |
| Provision edge | `sg edge setup *` | `Setup__IAM/ACM/Lambda/CF/DNS` (not built) | **Slice 5** |

The split is the natural one: the **read + pure-asset + measurement** surface is
fully exercisable now (it only reads DNS or runs in-memory), while the
**mutating fleet operations** (`boot`/`reconcile`/`drain`) and **provisioning**
(`setup`) need the Slice-5 EC2 seams and `Setup__*` classes the SG/Edge plan
already scopes.

# Package layout

A `cli/` package under `sg_compute_specs/sg_edge/`, modelled on
`vault_publish/cli/` + `vault_publish/setup/cli/`:

```
sg_compute_specs/sg_edge/cli/
  Cli__SG_Edge.py          umbrella typer: status/boot/reconcile/idle-check/drain
                           + add_typer(dns, proxy, bench, waker, setup)
  Cli__SG_Edge__Dns.py     dns sub-app (proxies/state/slugs/routing)
  Cli__SG_Edge__Proxy.py   proxy sub-app (user-data/nginx-conf/cf-function)
  Cli__SG_Edge__Bench.py   bench sub-app (scenario runner over Edge_Bench__Runner)
  Cli__SG_Edge__Waker.py   waker sub-app (status/invoke/logs)
sg_compute_specs/sg_edge/setup/
  service/Setup__IAM|ACM|Lambda|CF|DNS.py   Slice-5 provisioning (compose sg aws *)
  cli/Cli__SG_Edge__Setup.py                 setup sub-app (check/create/update/delete + per-area)
```

# Conventions (mirror `sg vp`, non-negotiable)

1. **Routes/commands have no logic** — each command builds the request, calls the
   service/reconciler/helper, and renders the result with `rich.Console`. All
   behaviour stays in the service classes (rule #19).
2. **Lazy imports inside command bodies** — keep `sg --help` fast and avoid
   importing the FastAPI/AWS stack at module load (the waker app needs py3.12).
3. **A `_svc()` / `_dns()` / `_reconciler()` factory** per sub-app, mirroring
   `Vault_Publish__Service().setup()`; the reconciler is built with the env-based
   config (`edge_parent()` etc. from `edge_waker__config`).
4. **`--parent` / `$SG_EDGE__PARENT_DOMAIN`** is the primary scope flag (defaults
   to `$SG_AWS__DNS__DEFAULT_ZONE`, same fallback the config already uses).
5. **Credential pre-flight + broad except** on the AWS-touching commands (STS
   GetCallerIdentity), rendering `ClientError`/`RuntimeError` as readable
   messages — copy `Cli__Setup`'s wrapper, no tracebacks.
6. **JSON output mode** (`--json`) on `status`/`dns *`/`bench` so the surface is
   scriptable and the bench honours doc-05's "JSON output only" decision.
7. **Type_Safe everywhere, one class per file, `═══` headers** — standard rules.

# Phasing

| CLI slice | Scope | Depends on |
|---|---|---|
| **CLI-1 (now)** | `cli/` package + register in `Cli__SG.py`; `status`, `dns *`, `proxy *`, `idle-check`, `bench` (core + local), `waker status/invoke` (local app). Tests: typer `CliRunner` against the in-memory DNS fake — no mocks. | nothing new (built logic only) |
| **CLI-2 (with Slice 5)** | `boot`, `reconcile`, `drain` wired to the live EC2 launcher/terminator; `waker logs`; the whole `setup *` surface. | SG/Edge Slice 5 (EC2 seams + `Setup__*`) |
| **CLI-3 (with Slice 6)** | bench scenario bodies (P-*/F-*/X-*) + `--target local|aws-bench` + docker-compose stack wiring behind `sg edge bench`. | SG/Edge Slice 6 (scenarios + stack) |

CLI-1 is shippable immediately and makes ~60% of the surface real: an operator
can inspect the fleet, read every DNS record, render the proxy boot assets, run
the idle counter, and drive the bench engine — all without live AWS.

# Testing

- **CliRunner unit tests** (`typer.testing.CliRunner`) per sub-app, asserting on
  exit code + rendered output, with `SG_Edge__DNS__Helper(route53=Route53__AWS__Client__In_Memory())`
  injected — same no-mocks pattern as the existing reconciler/DNS tests.
- **`--json` golden assertions** so the scriptable contract is locked.
- **`sg edge` registration test** — assert `sg edge` and `sg ed` resolve and that
  registering them did not perturb the existing top-level command set (the
  zero-impact guard, as a test).

# Open question for the owner

The brief names the bench `sg edge_bench` (underscore, top-level). This plan
makes `sg edge bench` canonical with `sg edge_bench` as a hidden alias, so the
whole edge surface lives under one `sg edge` umbrella. If you'd rather keep
`sg edge_bench` as the *primary* (separate top-level command, matching the brief
verbatim), it's a one-line change in `Cli__SG.py` — flag it and I'll flip the
default.
