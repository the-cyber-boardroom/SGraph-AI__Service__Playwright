# T2.6b — Finish the Safe_* primitives sweep

⚠ **Tier 2 — contract violation finish.** T2.6 commit `2b30ff1` covered ~10% of the brief. Pod__Manager — explicitly named in the original brief — was untouched.

## What's still wrong

The original T2.6 brief required sweeping raw `str`/`int` parameters across:

- `Section__Sidecar` — ✅ done
- `Pod__Manager` — ❌ **NOT TOUCHED**. `def list_pods(self, node_id: str)`, `def start_pod(self, node_id: str, ...)`, etc. — all still raw `str`.
- `Schema__Node__Create__Request__Base` — ⚠ partial; verify field types
- "Other sites" — ❌ spec-side raw types in service classes untouched

T2.6 commit message implied a wide sweep; reality was narrow. No PARTIAL flag, no T2.6b filed at the time. Found by review (2026-05-05 14:00).

## Tasks

1. **`Pod__Manager`** — replace every `node_id: str`, `pod_name: str`, etc. with `Safe_Str__Node__Id`, `Safe_Str__Pod__Name`. The primitives exist (created in T1.x); use them.
2. **Sweep spec-side service classes** — `sg_compute_specs/<spec>/service/<Pascal>__Service.py` for raw `: str` / `: int` / `: bool` parameters. Replace with primitives.
3. **Sweep schemas under `sg_compute_specs/`** — any `Schema__*` field still typed as raw should be a primitive.
4. **Sweep `EC2__Platform`** — any methods with raw `: str` parameters (`region`, `node_id`, etc.).
5. **Verify `Schema__Node__Create__Request__Base`** carries `Safe_Str__*` for `node_name`, `region`, `caller_ip`, `instance_type`, etc.
6. **Add new primitives only when needed** — one class per file under `sg_compute/primitives/`. Don't bloat.
7. **Update tests** — wherever a test passes a raw string to a method that now takes a primitive, wrap it: `Safe_Str__Node__Id('test-node-1')`.
8. **CI guard (optional)** — extend `tests/ci/test_no_legacy_imports.py` (or add a sibling) that flags raw `: str` / `: int` parameters in `sg_compute/core/` and `sg_compute/platforms/`. Catches future regressions.

## Acceptance criteria

- `grep -rn ': str' sg_compute/core/pod/` returns zero hits (or only justified internal helpers).
- `grep -rn ': str' sg_compute_specs/*/service/*.py` similarly clean.
- `grep -rn ': str' sg_compute/platforms/ec2/EC2__Platform.py` clean.
- `Pod__Manager.list_pods(Safe_Str__Node__Id('test'))` works; passing a raw string raises validation.
- All tests pass.
- Debrief honestly classifies T2.6 (the previous shipment) as `PARTIAL`-without-flag → **bad failure**.

## "Stop and surface" check

If you find a parameter where Safe_Str feels overkill (e.g. a debug-print string): **STOP**. The rule applies to schema fields and public method parameters. Internal helpers can use raw types.

If you find Pod__Manager calls passing raw strings from upstream callers (e.g. routes): **STOP**. The route should pass through `Safe_Str__Node__Id` from the parsed URL parameter. If the route's URL parameter parsing returns raw strings, that's a different fix in the route layer.

## Live smoke test

Construct a `Pod__Manager` and call `list_pods(Safe_Str__Node__Id('test-node'))` → no error. Call `list_pods('test-node')` → expect `TypeError` or validation error.

## Source

Executive review T2-implementation §"T2.6 — silent scope cut" (2026-05-05 14:00).
