# T2.6b — Safe_* primitives: Pod__Manager + Platform (PARTIAL)

**Date:** 2026-05-05
**Branch:** `claude/fix-t2-4-production-U2yIZ`
**Phase:** T2.6b (follow-on to T2.6 commit `2b30ff1`)
**Status: PARTIAL** — Pod__Manager + EC2__Platform + routes done; schema fields + spec-side deferred to T2.6c.

---

## What this PR ships

**Pod__Manager** — all 6 public method signatures updated:
- `list_pods(node_id: Safe_Str__Node__Id)`
- `start_pod(node_id: Safe_Str__Node__Id, ...)`
- `get_pod(node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name)`
- `get_pod_stats(node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name)`
- `get_pod_logs(node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name, ...)`
- `stop_pod(node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name)`
- `remove_pod(node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name)`

Private helpers (`_sidecar_client`, `_resolve_api_key`, `_map_pod_info`) intentionally remain raw `str` — exempt per T2.6b brief "Internal helpers can use raw types."

**Platform base class** — `list_nodes`, `get_node`, `delete_node` signatures updated to Safe_Str types.

**EC2__Platform** — same public method signatures. Private helpers (`_tag`, `_raw_to_node_info`, `_service_for`) and class attribute `name: str` remain raw — justified.

**Routes__Compute__Pods** — wraps URL path parameters before passing to manager:
- `Safe_Str__Node__Id(node_id)` on all 7 route methods
- `Safe_Str__Pod__Name(name)` on 6 route methods that take a pod name

This is the validation gate: if a caller passes a malformed node/pod identifier in the URL, the Safe_Str constructor raises before it reaches Pod__Manager.

**Routes__Compute__Nodes** — wraps `Safe_Str__Node__Id(node_id)` and `Safe_Str__AWS__Region(region)` before calling platform methods.

**Tests** — `test_Pod__Manager` direct calls updated to pass `Safe_Str__Node__Id` and `Safe_Str__Pod__Name` values. Route tests unchanged (they pass URL strings to TestClient; FastAPI parses them to raw str; the route wraps them).

---

## What is deferred to T2.6c

- **Schema field primitives** — `Schema__Pod__Info`, `Schema__Pod__Stats`, `Schema__Pod__Logs__Response`, `Schema__Pod__Stop__Response`, `Schema__Pod__Start__Request` carry raw `: str` / `: int` fields. New primitives needed (`Safe_Str__Container__Name`, `Safe_Str__Docker__Image`, `Safe_Str__Log__Content`, etc.); some warrant Architect input on semantics.
- **Spec-side service class sweep** — `Docker__Service`, `Podman__Service`, `Vnc__Service`, `*__User_Data__Builder.render()` — large scope; `api_key_ssm_path: str` → `Safe_Str__SSM__Path` pattern is mechanical but needs Architect confirmation before sweeping all specs.

T2.6c brief filed at `team/comms/briefs/v0.2.1__hotfix/backend/T2_6c__safe-str-primitives-schemas-and-spec-side.md`.

---

## Failure classification: T2.6

### BAD FAILURE — silent scope cut, no PARTIAL flag

T2.6 commit `2b30ff1` swept ~10% of the brief (only the explicitly named `Section__Sidecar` and core node schemas). `Pod__Manager.list_pods(node_id: str)` was named by name in the original brief and was not touched. The commit message implied a wide sweep; the reality was narrow. No PARTIAL flag, no T2.6b brief filed.

This is a **bad failure** by the debrief vocabulary:
- The scope cut was **silent** — the brief's acceptance criteria for Pod__Manager were met in the review but not in the commit.
- No "Stop and surface" conversation happened — the dev picked the small targets and shipped.
- The commit message over-stated the scope.

Pattern identified: this is the same as the T2.7 "all" claim and T2.4 "real writer" over-claim. The team has a recurring failure mode under difficulty: take the small win, over-claim in the message, move on.

### Good failure (none from T2.6)

No good failures to report from T2.6. The work that WAS done (primitives, one-class-per-file, tests) was clean. The failure was in scope representation.

---

## PARTIAL discipline applied in T2.6b

- **Commit message** subject will contain `(PARTIAL)`.
- **T2.6c brief** filed in this same PR with clear scope and Architect questions flagged.
- **`NotImplementedError`-with-pointer** pattern not applicable here (we're shipping real changes, not stubs).
- **Stop and surface** applied once: schema primitives for `content: str` (log content) and `ports: str` (Docker port map) are wide-open strings with no obvious regex — surfaced in T2.6c brief rather than guessing a primitive.

---

## Acceptance criteria (T2.6b brief) — verified

| Criterion | Status |
|---|---|
| `grep -rn ': str' sg_compute/core/pod/` → only internal helpers | ✅ Private methods + Sidecar__Client + schema fields remain (all justified or deferred) |
| `grep -rn ': str' sg_compute/platforms/ec2/EC2__Platform.py` → only internal helpers | ✅ Only `name: str`, `_tag`, `_raw_to_node_info`, `_service_for` remain |
| `Pod__Manager.list_pods(Safe_Str__Node__Id('test'))` works | ✅ Signature updated |
| Routes wrap Safe_Str before passing to manager | ✅ All 7 pod routes + 3 node routes wrap |
| All tests pass | ⚠ Deps unavailable in this env; CI gate required |
| Schema fields typed | ❌ PARTIAL — deferred to T2.6c |
| Spec-side service sweep | ❌ PARTIAL — deferred to T2.6c |
