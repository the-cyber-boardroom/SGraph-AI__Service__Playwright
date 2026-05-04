# v0.1.97 — Clean top-level `sp` command map

**Status:** PROPOSED — not yet implemented.
**Author:** Claude (per operator brief, 2026-04-29).
**Predecessor:** v0.1.96 stack-split (Phases A → D shipped).

After v0.1.96, the `sp` CLI looks like this at the top level:

```
sp create / list / info / delete / connect / shell / env / run / exec / exec-c /
   logs / diagnose / forward / wait / clean / create-from-ami / open / screenshot /
   smoke / health / ensure-passrole

sp vault / ami / elastic / opensearch / prometheus / vnc / linux / docker
```

21 stack-lifecycle commands at the top level, **all of them about the Playwright EC2 specifically**. Plus 8 visible subgroups, each owning its own section.

That's asymmetric:
- Every other section (`sp os`, `sp prom`, `sp vnc`, `sp linux`, `sp docker`, `sp el`, `sp ob`) gets a tidy subgroup.
- Playwright EC2 — itself just one stack type — gets the whole top level.

This brief proposes flattening that: **make Playwright a sister section like the others**, and reserve top-level for genuinely cross-cutting / global ops.

| Doc | Topic |
|---|---|
| 00 (this) | Overview + reading order |
| [`01__current-shape.md`](./01__current-shape.md) | What `sp --help` shows today, line by line |
| [`02__proposed-shape.md`](./02__proposed-shape.md) | The clean target — `sp pw <cmd>` for Playwright; only global ops at top |
| [`03__migration-plan.md`](./03__migration-plan.md) | Concrete commits; mostly decorator moves (same shape as Phase D D.3/D.4) |
| [`04__open-questions.md`](./04__open-questions.md) | Choices needing operator sign-off before Dev starts |

## TL;DR

```
# Today (post v0.1.96)
sp create                       # Provision Playwright EC2
sp vault clone <key>            # Vault op on Playwright EC2
sp ami create                   # Bake AMI from Playwright EC2

# Proposed (v0.1.97)
sp pw create                    # Provision Playwright EC2
sp pw vault clone <key>         # Vault op on Playwright EC2
sp pw ami create                # Bake AMI from Playwright EC2

# Top level reserved for:
sp catalog                      # Cross-section enumeration (mirrors /catalog/*)
sp doctor                       # Global preflight (account, region, ECR, IAM)
sp --version
sp --help
```

Same shape, same code — just relocated under `sp pw` so the Playwright EC2 stops being special-cased.

## Why now

- `sp os` / `sp prom` / `sp vnc` shipped — symmetry now pays off (one mental model for all stacks).
- The MVP UI in v0.1.101 drives off `GET /catalog/stacks` — having `sp pw` show up alongside the others lets the UI list Playwright stacks the same way it lists the rest.
- The `sp ami` subgroup currently operates on Playwright AMIs only, but that's not obvious from its name. `sp pw ami` makes scope explicit.
- Likewise `sp vault` operates on the Playwright EC2's vault checkout. `sp pw vault` makes that explicit.

## Why not now

- Hard cut means breaking every operator's muscle memory in one commit (`sp create` → `sp pw create`). Plan doc 7 C1 sets the precedent (no transition window), but this is a much bigger UX change.
- The migration is mechanical (decorator moves) but the surface is large (~21 commands).
- Tests + smoke + any operator runbooks reference the flat names.

## Estimate

| Slice | Roughly |
|---|---|
| `sp pw` subgroup + move 21 commands | ~1 day, single commit, mostly decorator moves |
| Move `sp vault` under `sp pw vault` | ~1 hr |
| Move `sp ami` under `sp pw ami` | ~1 hr |
| Add `sp catalog` (mirror /catalog/*) | ~half-day |
| Add `sp doctor` (factor `ensure-passrole` + preflight bits) | ~half-day |
| Update tests + runbooks | ~half-day |

Total: ~2.5 days. One PR, hard cut.
