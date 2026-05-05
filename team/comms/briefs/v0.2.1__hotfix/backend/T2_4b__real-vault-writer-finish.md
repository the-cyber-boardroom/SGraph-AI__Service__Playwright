# T2.4b — Real vault writer (T2.4 still broken in production)

🔴 **BLOCKING.** T2.4 commit `f8fbd52` was reviewed 2026-05-05 14:00 and found to be **fake-stub 2.0**. This brief replaces T2.4. Ship as one PR before any further T3+ work.

## What's still wrong

1. `Vault__Spec__Writer.vault_attached: bool = False` (default).
2. `Fast_API__Compute.py:159` wires it as `Vault__Spec__Writer(spec_registry=self.registry)` — does NOT pass `vault_attached=True`.
3. **Every prod PUT returns 409.** The "real writer" is unreachable from production traffic.
4. `test_Routes__Vault__Spec.py` mounts the route class without `prefix='/api/vault'`, so the test hits `/vault/spec/...` — exactly the prefix-bypass bug the original T2.4 brief warned against, repeated.
5. The "in-memory dict" backing store is ephemeral by design (resets every process boot) — fine as a transitional layer if `vault_attached=True` AND properly wired, NOT as a stand-in for a real vault.

## Why this happened

The dev shipped before the previous T2 review landed (they were mid-flight). The original T2.4 brief explicitly named the antipattern ("if the test passes against a fake handler but you're not sure the real route is hit: STOP"). The dev did the pattern.

This brief is the patch — and the conversation. **Read the original T2.4 brief AND the executive review at `team/humans/dinis_cruz/claude-code-web/05/05/14/00__executive-review__T2-implementation.md` before starting.**

## Tasks

1. **Decide the vault backing store** with Architect. Options:
   - (a) **Real vault wired now** — read/write through the existing vault layer at `sgraph_ai_service_playwright__cli/vault/` (or wherever it lives post-BV2.9). Per-Node vault-token resolution.
   - (b) **In-memory dict, but `vault_attached=True` by default** — transitional storage, real route flow, real round-trip semantics. Promote to real vault in v0.3.
   - (c) **In-memory dict + explicit feature flag** — `vault_attached` opt-in via env var; default off in CI, on in local dev / staging.
   Recommend **(b)** for v0.2.1.x — fastest path to a working `/api/vault/*` surface; real vault wiring is a separate brief in v0.3.
2. **Flip `vault_attached=True`** in `Fast_API__Compute._mount_control_routes`. Add a comment: `# in-memory store for v0.2.x; real vault wiring tracked in v0.3`.
3. **Fix the route test** — mount with `prefix='/api/vault'`. Use `TestClient(fast_api.app())` and hit the real URL `/api/vault/spec/{spec_id}/{stack_id}/{handle}`. Assert the URL is what production sees.
4. **Round-trip test** — write 1KB blob via PUT, read metadata via GET, assert SHA256 matches. **No bypass; no patch; no mock.**
5. **Routes return `<schema>.json()`** — not raw dicts. Sweep `Routes__Vault__Spec` for any dict returns.
6. **Verify the URL prefix is single `/vault/`** — a regression check. Grep for `/api/vault/vault/` and `/vault/vault/` returning zero.
7. **Live smoke test** — `curl -X PUT -H "X-API-Key: $KEY" -d "hello" http://localhost:8000/api/vault/spec/firefox/test-node/test-handle` returns the receipt; `curl http://.../metadata` returns the SHA256 of "hello".

## Acceptance criteria

- `vault_attached=True` in production wiring path.
- Route test uses the real prefix; no `prefix=` argument missing.
- Round-trip test passes against the real route.
- All routes return typed schemas (no raw dicts).
- `grep "vault/vault" sg_compute/` returns zero hits.
- Live smoke test in PR description (curl output or screenshot).
- Debrief explicitly classifies T2.4 (the previous shipment) as a **bad failure** per the new debrief vocabulary.

## "Stop and surface" check (re-read this one)

If you find yourself thinking _"I'll mount the route class without the prefix in the test because it's faster"_: **STOP**. That's the exact bug. The test must hit the real URL.

If you find yourself thinking _"the in-memory dict is fine, no need to flip vault_attached"_: **STOP**. Read the production wiring path. If `vault_attached=False` is the default, every prod write returns 409.

## Source

Executive review T2-implementation (2026-05-05 14:00) §"The most important finding — fake-stub 2.0".
