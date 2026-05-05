# T2.6 — Replace raw `str` / `int` with `Safe_Str__*` / `Safe_Int__*`

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

Brief mandates Safe_Str__* / Safe_Int__* primitives for all method parameters and schema fields. Code review found raw primitives across:

- `Section__Sidecar.render(registry: str, image_tag: str, port: int)` — should be `Safe_Str__Image__Registry`, `Safe_Str__Image__Tag`, `Safe_Int__Port`.
- `Pod__Manager.list_pods(node_id: str)` — should be `Safe_Str__Node__Id`.
- `Schema__Node__Create__Request__Base` — fields like `stack_name : str = ''` — should be `Safe_Str__Node__Name | None`.
- Likely other sites: `Pod__Manager` other methods, `EC2__Platform.create_node` parameters, every other `Routes__*` body schema.

## Tasks

1. **Sweep `sg_compute/` and `sg_compute_specs/`** — `grep -rn ': str' --include="*.py" sg_compute/ sg_compute_specs/` — sample the hits, replace with `Safe_Str__*`.
2. **Same for `: int`, `: bool`, `: float`, `: list`, `: dict`** — these are forbidden as schema field types per the project rules.
3. **Create new `Safe_Str__*` / `Safe_Int__*` types** as needed. Each gets its own file under `sg_compute/primitives/` (one class per file).
4. **Specifically named in the review**:
   - `Safe_Str__Image__Registry` — validates Docker registry hostnames.
   - `Safe_Str__Image__Tag` — validates Docker tag format.
   - `Safe_Int__Port` — bounded 1-65535.
   - `Safe_Str__Node__Name` — auto-name format or operator-supplied; allowlist of chars.
5. **Fix the `Schema__Node__Create__Request__Base`** — `stack_name` field stays as a name with `Safe_Str__Node__Name | None` (default None for auto-generation). **And rename**: `stack_name` is wrong vocabulary post-v0.2 — should be `node_name`.

## Acceptance criteria

- `grep -rn ': str' --include="*.py" sg_compute/ sg_compute_specs/` shows only allowed sites (e.g. inside `Safe_Str__*` definitions themselves, or operator-input parsing).
- Same for `: int`, etc.
- New primitives have unit tests.
- All existing tests still pass.

## "Stop and surface" check

If you find a parameter where Safe_Str feels overkill (e.g. an internal-only string that's never untrusted): **STOP**. The rule is hard. If it's truly a contract escape, surface to Architect — but the answer is almost always "make a primitive".

## Live smoke test

Try to construct a Schema with an invalid value (e.g. port 99999) → expect `ValueError` from the Safe_Int validation.

## Source

Executive review Tier-2; backend-early review §"Top contract violation #3".
