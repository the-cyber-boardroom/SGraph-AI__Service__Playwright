# sentinel — Reality Index

**Domain:** `sentinel/` | **Last updated:** 2026-05-23 | **Maintained by:** Dev (landing) → Librarian (verify)
**Code-source basis:** `sgraph_ai_service_playwright__cli/sentinel/` (branch `claude/gracious-galileo-fNYWn`, not yet merged to `dev`) + the 05/22 SG/Sentinel brief series.

SG/Sentinel is the edge-guard product surface: real-time request **logging** and obvious-bad **blocking** at the CDN edge. **L1 decides and signals; L2 acts and writes.** Distinct from SG/Edge (which runs workloads) — Sentinel guards what sits in front of them.

---

## EXISTS (code-verified, MVP)

### CLI surface — `sg sentinel` (alias `sn`)

Mounted in `sg_compute/cli/Cli__SG.py` as a top-level peer surface.

| Command | Does |
|---------|------|
| `sg sentinel rules list/show/test` | The six tiny-core rules; `test` runs the real node L1 engine over the canonical set |
| `sg sentinel local up/hit/down [--docker]` | Offline full stack — local-direct (node) or the `--docker` CF-env sim |
| `sg sentinel logs ls/tail/trace` | Read the log sink (use case 1) |
| `sg sentinel blocks list/why` | Inspect blocked requests + reasons (use case 2) |
| `sg sentinel deploy create/destroy/teardown` | Live AWS (mutation-gated `SG_AWS__SENTINEL__ALLOW_MUTATIONS=1`) |
| `sg sentinel status` | What's deployed (L1 function / L2 lambda) |

### The signal spine

`Schema__Sentinel__Signal` (snake_case, byte-identical across all targets): `request_id`, `aws_request_id`, `captured` (`Schema__Sentinel__Captured`), `verdict` (allow/block), `reason`, `rule_id`, `action` (pass/drop_403/deflect_404), `layer` (L1), `engine_version`, `ruleset_version`. Transport = raw-JSON `x-sentinel-signal` request header on AWS; in-process locally. `Signal__Codec` encodes/decodes.

### L1 engine (decide + signal only, no I/O)

`runtime/layer1/sentinel_l1.js` — single, dependency-free, CloudFront-Functions-2.0-compatible. Six rules, first-block-wins: `0007` malformed, `0003` banned-ip, `0012` path-never-valid, `0014` hidden-file, `0018` wp-scan, else `0001` capture-all (allow). `BANNED_IPS` is inlined from `rules.embedded.json` by `Sentinel__L1__Source` (local/docker) and by `Sentinel__Deployer` (CF) — single source. `Sentinel__Rule__Registry` holds the Python-side metadata.

### L2 actor (sole actor + sole I/O owner)

`runtime/layer2/Sentinel__L2__Actor` — `enforce` (block→403/404, allow→pass), `build_record`, `write` to a `Log__Sink`. Never re-evaluates rules. `privacy_mode` defaults to `hash` (sha256[:12] of source IP); also `plain`/`omit`. `runtime/layer2/lambda_handler.py` is the Lambda@Edge origin-request adapter (`handle_request` is the testable core).

### Sinks (`service/log_sink/`)

`Log__Sink` base (shared key layout `<prefix>/YYYY/MM/DD/HH/<request_id>.json`, one object per record) + `InMemory__Log__Sink`, `Local_FS__Log__Sink` (dir overridable via `SG_SENTINEL__LOCAL_SINK_DIR`), `S3__Log__Sink` (wraps `S3__AWS__Client`).

### Targets

- **B local-direct** — `Sentinel__Local__Harness`: real node L1 + real Python L2 in-process → local-FS sink. Fully offline.
- **C local-docker** — `Sentinel__Docker__Runtime/Harness`: CF-env sim container (`runtime/local/docker/`) running the same `sentinel_l1.js` behind an HTTP listener.
- **A live AWS** — `Sentinel__Deployer` composes `S3__AWS__Client` + `CloudFront__Function__AWS__Client` + `Lambda__Deployer` + `CloudFront__AWS__Client` (cache-disabled distribution; CF Function on viewer-request, L@E numbered version on origin-request). Full lifecycle unit-tested via `Sentinel__Deployer__In_Memory`.

### Role profiles (`service/Sentinel__Role__Profile.py`)

`sentinel` (operator, account-root trust: CF/Lambda/S3 + `iam:PassRole`) and `sentinel-edge` (Lambda@Edge **execution** role, `trust_services` = `lambda.amazonaws.com` + `edgelambda.amazonaws.com`, `s3:PutObject` + CloudWatch Logs). Self-registered in `AWS__Role__Profiles._ensure_loaded()`.

### Parity matrix

`tests/.../sentinel/parity/` — canonical request set asserted against the local-direct baseline (always runs, node-gated); docker (B↔C) and live AWS legs gated and skip without docker/creds.

---

## NOT IN THE MVP (PROPOSED — does not exist yet)

Fingerprint/fast-track; any rule evaluation at L2; Layer 3 async/LLM; fractal-graph traversal; rules-as-vault; evidence/compliance graphs; threat-intel; multi-CDN; SSL termination; cache-hit logging (needs viewer-response path); log batching; IP-escrow privacy mode; the **TUI** (CLI-first for the MVP — the CLI is TUI-API-friendly via `--json`). See `proposed/index.md`.

---

## Known gaps (flagged in the debrief)

- Live Lambda@Edge **packaging** (full dependency zip + code-size budget) and **replica-deletion timing** are only exercised by the gated Phase-5 smoke test — not yet run live.
- Per-resource `sg:*` **tagging** is not wired (the `Enum__AWS__Surface.SENTINEL` member exists; the S3/CF/Lambda create paths don't thread tags through yet).
