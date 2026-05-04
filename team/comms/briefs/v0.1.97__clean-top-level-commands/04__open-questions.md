# Open questions for sign-off

Tagged so the operator can answer in one pass before Dev starts.

## Q1 — Long form name: `sp pw` vs. `sp playwright`?

The other sister sections use `sp el`/`sp os`/`sp prom` as primary short aliases with the long forms hidden. But for the headless-API-Playwright stack, the two reasonable choices are:

- **`sp playwright`** as long form, **`sp pw`** as short alias (matches `el`/`os`/`prom`/`lx`/`dk` precedent)
- **`sp pw`** as the only name (no long form)

**Default if unanswered:** `sp playwright` long, `sp pw` short alias hidden — matches the existing convention.

## Q2 — Hard cut or transition window?

Phase D D.3/D.4 (v0.1.96) used a hard cut per plan doc 7 C1. Same rule here?

- **Hard cut:** `sp create` returns "command not found" the moment the commit lands. Operators retrain immediately.
- **Transition window:** keep flat aliases for one minor version (`sp create` quietly delegates to `sp pw create`), then hard-drop next version.

The brief assumes hard cut to match precedent, but the impact of changing 21 commands at once is meaningfully bigger than the 7+4 of D.3/D.4.

**Default if unanswered:** hard cut (matches v0.1.96 precedent + reduces forever-tech-debt).

## Q3 — `sp ensure-passrole` — keep or fold into `sp doctor`?

It's currently a top-level command. The brief proposes folding into `sp doctor passrole`.

- **Fold:** symmetry — every preflight is under `sp doctor`. Run-all becomes `sp doctor`.
- **Keep:** an existing top-level alias as a quality-of-life shortcut for the most common preflight (Lambda → EC2 PassRole errors).

**Default if unanswered:** fold (every preflight under `sp doctor`).

## Q4 — `sp doctor` scope: just preflight, or include health checks?

The proposed `sp doctor` is for **before-create** checks (account / region / ECR / IAM). Section-specific health checks (e.g. `sp pw health <name>`) stay in their sections.

But there's a third class — **post-deploy environment checks**: "is my AWS account in a fit state to run any sp command?" Could land under `sp doctor` or a new `sp env` (different from the existing per-instance `sp env`).

**Default if unanswered:** `sp doctor` covers preflight (before-create) only. Per-instance health stays per-section.

## Q5 — `sp catalog` API parity

The proposed `sp catalog types` / `sp catalog stacks` mirrors `GET /catalog/*`. Should the CLI fall back to direct AWS calls (composing each section's service) or call the local FastAPI service via a hidden in-memory invocation?

- **Direct AWS:** simpler; CLI works without the FastAPI server running. The catalog service is a Type_Safe class with no HTTP coupling — just inject sub-services and call `list_all_stacks()`.
- **Via FastAPI:** ensures CLI and API can never drift. But adds a startup cost (osbot-fast-api boot) on every `sp catalog` invocation.

**Default if unanswered:** direct AWS (matches every other typer command in this codebase).

## Q6 — When?

This is a v0.1.97 candidate. Three options:

1. **Now (next branch).** Lock the clean shape in before more downstream code references the old names.
2. **After the API rewiring** (the immediate VNC handover). Fast_API__SP__CLI changes are smaller and don't touch the typer surface.
3. **Defer.** Ship UX polish + new section work first; cleanup landing v0.1.99+.

**Default if unanswered:** option 2 — finish the open `Fast_API__SP__CLI` wiring (VNC at minimum) first, then this is a single-PR clean-up the next session after.

---

Once these six are answered, Dev can start straight from `03__migration-plan.md`. Each commit there is mechanical and testable.
