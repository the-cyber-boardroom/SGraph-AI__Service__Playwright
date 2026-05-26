# sg-compute — Proposed

PROPOSED — does not exist yet. Items below extend the SG/Compute domain but are not in code today.

Last updated: 2026-05-25 | Domain: `sg-compute/`

---

## P-1 · `Section__Sidecar` user-data composable (BV2.2)

**What:** A user-data section that renders the ECR-login + `docker run` block for the host-control sidecar on every Node.

**Status note:** Listed as PROPOSED in the original 545-line index. Code at `platforms/ec2/user_data/Section__Sidecar.py` does exist (recorded in [`../platform.md`](../platform.md)). Keep this entry until the reality doc + brief are reconciled, since the BV2.2 wiring of all 10 spec `User_Data__Builder` classes still has loose ends per the history log.

## P-2 · Per-spec `Spec__Service__Base` common lifecycle base class

**What:** A shared base class that all per-spec `*__Service` classes (Docker, Ollama, Open_Design, …) extend, with default `health/exec/connect_target` implementations and a uniform `create_node` contract.

**Status note:** A `Spec__Service__Base` was introduced in v0.2.6 (see [`../specs.md`](../specs.md)). This proposed item tracks the broader rollout — i.e. migrating every spec service to the base class (today only `Ollama__Service` extends it).

## P-3 · `Node__Identity` — node-id generation/parsing helper

**What:** A small helper that owns node-id generation and parsing (today the logic is sprinkled across `Stack__Naming`, the per-spec mappers, and the EC2 helpers).

## P-4 · Remaining legacy specs migrated to `sg_compute_specs/` (phases 3.1–3.8)

**What:** Move the remaining legacy specs into the `sg_compute_specs/` tree following the same shape used for `docker` (B3.0): `linux`, `podman`, `vnc`, `neko`, `prometheus`, `opensearch`, `elastic`, `firefox`.

## P-5 · Vault-sourced sidecar API key

**What:** Follow-on to BV2.9 — wire the sidecar API key to be sourced from the vault rather than the current persistence stub.

## P-6 · Real vault I/O (v0.3 follow-on)

**What:** `Vault__Spec__Writer` currently uses an in-memory dict with `vault_attached=True`. Persistent vault wiring is deferred to v0.3.

## P-7 · SG/Edge — central edge tier (v0.2.37)

**What:** A central edge that terminates TLS once (CloudFront + wildcard ACM), routes by slug to ephemeral vault targets via an OpenResty proxy fleet, and scales to zero. **DNS-as-registry, no coordination service:** `_sg.<slug>` TXT records carry routing metadata, `proxies.<parent>` A records carry fleet membership, and a `_state.<parent>` TXT record holds the idle-teardown counter. The Edge Waker is a convergent `Serverless__Fast_API` Lambda (cold-cold bootstrap + reconciliation toward a target proxy count), kept separate from the existing Vault Waker.

**Design:** [`briefs/05/20/sg-edge/sg-edge__01..05`](../../../../../humans/dinis_cruz/briefs/05/20/sg-edge/) (5 briefs; rewritten `647de5a`). FastAPI-Lambda technique: [`briefs/05/20/fast-api/`](../../../../../humans/dinis_cruz/briefs/05/20/fast-api/). **Plan:** [`team/comms/plans/v0.2.37__sg-edge/README.md`](../../../../../comms/plans/v0.2.37__sg-edge/README.md) — re-grounds the briefs onto existing `sg aws *` modules (`cf` incl. `CloudFront__Origin__Failover__Builder`, `acm`, `dns`, `ec2`, `iam`, `lambda_`) and the in-repo Lambda template `vault_publish/lambdas/waker/` + `sg_compute/_for_osbot_aws/`. No new AWS primitive needed (the earlier S3 `If-None-Match` plan was dropped when the brief removed the lock).

**Status note:** Slice 1 (typed foundation) has LANDED and is EXISTS — see the `sg_edge — Phase 1 foundation` section in [`../index.md`](../index.md). Slices 2–6 (DNS helper, Edge Waker FastAPI Lambda, proxy rig + CF Function, setup/wiring, `sg edge_bench` harness) remain PROPOSED. Purely additive — zero impact on existing `sg *` commands.

## P-8 · `sg vscode` — VS Code on EC2 compute spec

**What:** A new top-level compute spec (`sg_compute_specs/vscode/`) that launches an ephemeral EC2 node running VS Code server, so VS-Code-dependent tooling (agentic coding extensions, language servers, app builders) runs on remote compute instead of the laptop. Two access modes: **SSM port-forward** (default — editor on loopback, no inbound ports, reached via `AWS-StartPortForwardingSession`) and **public HTTPS** (Caddy `:443` + auth portal, optional Auto-DNS). Plus the free SSM-shell terminal path from `Spec__Service__Base.connect_target`.

**Reuse:** clones `local_claude` (SSM-only EC2 skeleton), `vault_app`'s SSM-forward surfacing (`Schema__Vault_App__Info.ssm_forward`, `Vault_App__Stack__Mapper.py:76`, `Cli__Vault_App.py` `forward`), `vnc`'s Caddy/auth/SG templates, the `sg_compute/platforms/ec2/` helpers + `Section__*` user-data, and `Vault_App__Auto_DNS`. Net-new is small: the `vscode/` package files, a `Vscode__Compose__Template` (code-server / `code serve-web` container), two enums, a stack-name primitive, and the schemas.

**TUI:** includes a `sg vscode tui` dimension following the shared TUI pattern (`sgraph_ai_service_playwright__cli/tui/` `Tui__App` + `tool_api/Tui_Api__Provider`; canonical example `sg_compute_specs/sg_edge/tui/`) — a read-only stacks dashboard over the native CLI with capability-gated actions. GUI-over-the-CLI per `library/guides/v0.2.39__tui_cli_separation.md`; lands after the native CLI (slice 6).

**Decisions (ratified 2026-05-25):** web/browser VS Code only (no remote desktop); v1 defaults to code-server (Open VSX), with official `code serve-web` (full MS marketplace) behind `Enum__Vscode__Distribution` for feature parity; fully ephemeral (vault-managed data is a later follow-on); no `--git-repo` seeding (post-connect); no `code tunnel` (SSM-forward is the only tunnel).

**Design:** [`library/docs/specs/v0.2.41__spec__vscode-on-ec2.md`](../../../../../../library/docs/specs/v0.2.41__spec__vscode-on-ec2.md). **Status note:** Net-new — does not exist in code. Purely additive — zero impact on existing `sg *` commands. Decisions ratified; ready for Dev to scaffold Slice 1.

---

## See also

- [`../index.md`](../index.md) — SG/Compute cover sheet
- [`../specs.md`](../specs.md) — vault writer and pilot specs
- [`../platform.md`](../platform.md) — `Section__Sidecar` (P-1)
- [`../cli.md`](../cli.md) — CLI surface (P-2 follow-on)
