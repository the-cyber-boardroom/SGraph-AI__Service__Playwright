# T2.2 — Build the firefox per-spec CLI (BV2.6 picked the wrong target)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

BV2.6 brief explicitly named **firefox** as the per-spec CLI target — vault-write commands (set credentials, upload MITM script). It explicitly named **docker** as a likely SKIP (the generic CRUD verbs cover it). The dev built docker. Firefox CLI never started.

This is the silent-scope-cut pattern: pick the easier target, mark "done".

## Tasks

1. **Write `sg_compute_specs/firefox/cli/firefox_commands.py`** as a Typer sub-app. Initial verbs (per BV2.6 brief intent):
   - `sg-compute spec firefox set-credentials --node {id} --username {u} --password {p}` — calls per-spec `PUT /api/specs/firefox/{node_id}/credentials`.
   - `sg-compute spec firefox upload-mitm-script --node {id} --file {path}` — calls per-spec `PUT /api/specs/firefox/{node_id}/mitm-script` with the file uploaded via the vault-write contract.
2. **If the per-spec routes don't yet exist** for these (the BV2.6 brief assumed they would by now): file a follow-up brief T2.2b for the routes; ship the CLI with `NotImplementedError` placeholders calling them. **Mark this PR PARTIAL.**
3. **Verify the dispatcher** — `sg-compute spec firefox list-verbs` should return the new verbs; `sg-compute spec firefox set-credentials --help` should print Typer help.
4. **Decide whether to keep the docker CLI** or remove it (since the brief said it should be skipped). Recommend: keep but add a header comment marking it experimental / out-of-scope.

## Acceptance criteria

- `sg_compute_specs/firefox/cli/firefox_commands.py` exists.
- At least 2 firefox-specific verbs work (or raise `NotImplementedError` with a clear "see T2.2b" message; debrief PARTIAL).
- Dispatcher (`sg-compute spec firefox <verb>`) routes correctly.
- `sg-compute spec validate firefox` still passes.

## Live smoke test

`sg-compute spec firefox set-credentials --node test-node --username u --password p` — at minimum, the command parses and reaches the per-spec service (even if the route isn't there yet, the dispatcher proves the wiring).

## Source

Executive review Tier-2; backend-early review §"Top missed requirement #2".
