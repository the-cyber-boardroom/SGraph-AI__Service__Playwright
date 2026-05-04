# 03 — Forward Roadmap

**Status:** PROPOSED — **architectural target only, no implementation in this brief**
**Read after:** `01__plugin-registry-design.md`, `02__event-bus-design.md`

---

## What this doc gives you

A statement of the architectural targets that this brief consciously **does not implement** but explicitly leaves room for. Two big pieces:

1. **Per-instance FastAPI control-plane container** — uniform "every instance runs a small FastAPI we manage; comms are API-only, never SSH."
2. **Vault-as-event-bus** — events written to a vault file as the durable, cross-process replacement for the in-process bus.

Both are pieces the source memo described as core to v0.22.19. Both are bigger than they look. Both are best done in their own focused brief once the structural prerequisites in this brief have landed. **Do not build either of these in this slice.** This doc exists so the architecture is recorded and so the implementing session for this brief leaves the right hooks in place.

---

## Forward target #1 — Per-instance FastAPI control plane

### What the source memo asks for

> Every EC2 instance we start (except possibly bare Linux terminals) runs a FastAPI container as the communication channel. This is the instance-level API that the platform backend talks to.
>
> The FastAPI container:
> - Is configured with a random API key (generated at instance start, stored in the vault for that session)
> - Exposes health, status, and plugin-specific endpoints
> - Is the only way the platform communicates with the instance
>
> This means the platform never SSHs into instances. All communication is API-driven, authenticated, and auditable.

### Why this is its own brief, not part of this one

The current platform talks to instances via different mechanisms per type:

| Type | Today |
|---|---|
| Linux | SSM `start-session` — no instance-side service. Operator opens a shell, types commands. |
| Docker | SSM — same as Linux. The Docker daemon is the actual remote API but operators don't talk to it. |
| Elastic | HTTP probes to Elasticsearch port 9200; SSM for shell access. The Elasticsearch API itself is the "control plane." |
| VNC | HTTPS via Caddy that the instance runs anyway. No separate platform-management API. |
| Prometheus | HTTP to port 9090 — same shape as Elastic. |
| OpenSearch | (similar — when active) |

Introducing **a uniform platform-managed FastAPI on every instance** is a significant change to:

1. **Every AMI build.** The image needs to start the FastAPI on boot, with a random API key passed via user-data, registered against the vault. That's six AMI build pipelines + tests.
2. **Every per-type service.** `Linux__Service`, `Docker__Service` etc. need to learn how to call the per-instance FastAPI for health, status, exec — replacing the SSM/SSH-shaped paths.
3. **Vault writes from instance side.** The instance needs IAM permission to write its own session record. That's a new IAM role pattern.
4. **Operator ergonomics.** Operators currently get a shell via SSM. If "no SSH" is a hard rule, we need to provide `sp linux exec` / `sp docker exec` that goes through the per-instance FastAPI — replacing SSM as the human-facing path. That's a UX shift, not just an architectural one.
5. **Networking.** The platform needs to reach the per-instance FastAPI. Either (a) public IP + auth, (b) VPC-internal call (works on EC2 platform but not from Lambda without VPC config), (c) reverse-tunnel.

**Doing all of this safely** is a multi-week piece. Trying to do it inside the plugin-restructure brief turns a 5-day refactor into a 4-week sprint that risks both the structural and the per-instance changes shipping half-baked.

### What this brief leaves in place to make the future brief easier

1. **Plugin manifest already declares `service_class()`.** The future brief can extend `Plugin__Service__Base` with a contract: `connect_to_instance(instance_id) -> Instance__API__Client` that each plugin implements.
2. **Event bus already in place.** `linux:stack.created` already fires; the per-instance setup-completed event (`linux:instance.api.ready`) becomes a natural addition.
3. **No code in this brief assumes SSM is the only path.** All per-type services already have their own client classes — the platform path is per-plugin, not centralised.

### Sketch of what the future brief will likely contain

- A new core sub-package: `core/instance_client/` with `Instance__API__Client` (HTTP client with API-key auth + retry).
- A new vault path: `sp-cli/instances/{instance_id}.json` storing per-instance API key + endpoint + health.
- AMI build changes: each AMI bakes a small "platform-agent" FastAPI image; user-data starts it with a random key and writes to vault.
- Per-plugin migration: `Linux__Service.execute_command()` replaces `ssm_session_start()` with `instance_api_client.exec()`. Same per other types.
- A "no SSH" lint check at deploy time — surface area audit.
- Operator UX: `sp linux exec <cmd>` or admin UI exec panel.

Suggested labelling: **`v0.23.x__per-instance-control-plane`** or similar.

---

## Forward target #2 — Vault-as-event-bus

### What the source memo asks for

The source memo doesn't directly call this out, but the broader architectural ambition is "events are durable, auditable, observable across processes." In-process is fine for now; vault-as-bus is the natural way to get those properties without bringing in Redis or EventBridge.

### What it would look like

Events become files in a known vault location:

```
sp-cli/events/
  2026-04-29/
    {iso-timestamp}__{event-name}__{nonce}.json
```

Each file contains:

```json
{
  "event_name": "vnc:stack.created",
  "timestamp":  "2026-04-29T14:32:08.123Z",
  "payload":    {"type_id": "vnc", "stack_name": "vnc-quiet-fermi", "region": "eu-west-2", ...},
  "emitter":    {"plugin": "vnc", "process_id": "lambda:abc-123"}
}
```

`emit()` becomes "write the file via `writeVaultFile`." `on()` becomes "subscribe to the vault prefix and dispatch to handlers" — implemented via a polling watcher initially, possibly websocket-style later.

### Why this is its own brief, not part of this one

1. **It needs the in-process pattern bedded in first.** Plugins emitting against an in-process bus is the testing ground; once the events stabilise, swapping the implementation is a one-class change.
2. **It depends on per-instance FastAPI being clear** — events written from instances need the same vault-write path as the rest of the per-instance plumbing.
3. **Polling vs streaming** is a real design question. Vault doesn't currently expose change-notification — listeners would poll. That's a whole sub-brief on its own.
4. **Cost & rate-limit modelling.** Every event = a vault write. At 100 events/min that's 144,000 writes/day = real money + real rate limits. Need to design batching and retention.

### What this brief leaves in place to make the future brief easier

- The bus API surface (`emit`, `on`, `listener_count`, `reset`) is **deliberately small** so it can be re-implemented against vault.
- The naming convention (`{plugin}:{noun}.{verb}`) maps cleanly to filename prefixes.
- `Schema__Stack__Event` and friends are Type_Safe → trivially serialisable to JSON for vault writes.

Suggested labelling: **`v0.23.x__vault-event-bus`** or similar.

---

## How to think about the two together

| Capability | This brief | Per-instance brief | Vault-bus brief |
|---|---|---|---|
| Plugin folders + manifests | ✅ ships | unchanged | unchanged |
| Plugin registry | ✅ ships | unchanged | unchanged |
| Catalog service consumes registry | ✅ ships | unchanged | unchanged |
| In-process event bus | ✅ ships | ⚠ may add events for `instance.api.ready` etc. | ⚠ implementation swapped to vault-backed; same API |
| Per-instance FastAPI on AMIs | ❌ no | ✅ ships | unchanged |
| `Instance__API__Client` core class | ❌ no | ✅ ships | unchanged |
| Per-plugin migration to API-only comms | ❌ no | ✅ ships per type | unchanged |
| Vault file path `sp-cli/events/...` | ❌ no | ❌ no | ✅ ships |
| Cross-process event durability | ❌ no | ❌ no | ✅ ships |

The two future briefs are **independent of each other**. Either can land first. Both depend on this brief landing first.

---

## What the implementing session should do *because* of this doc

Two small things, only:

1. **When writing the in-process `Event__Bus`,** keep the API surface to exactly what's specified in doc 02. Resist adding helpers (`emit_async`, `wait_for_event`, etc.) — those won't translate cleanly to the vault-bus implementation.

2. **When writing per-plugin `service` classes that emit events,** put the `event_bus.emit(...)` at the **success path of the public method**, not deep in private helpers. This way, when the implementation swaps to vault-bus, the emit sites are easy to find and review.

That's it. **Don't pre-implement the future.** This doc exists so the architecture is on record.
