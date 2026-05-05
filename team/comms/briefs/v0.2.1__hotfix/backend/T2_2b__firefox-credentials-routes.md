# T2.2b — Firefox per-spec credentials + MITM script routes

⚠ **Tier 2 follow-up from T2.2.** Standalone PR.

## What's missing

T2.2 shipped `Cli__Firefox` with `set-credentials` and `upload-mitm-script` commands, but the per-spec API routes they call don't exist yet:

- `PUT /api/specs/firefox/{node_id}/credentials` — set HTTP basic-auth credentials on a running firefox node
- `PUT /api/specs/firefox/{node_id}/mitm-script` — upload a mitmproxy intercept script

Both CLI commands currently raise `NotImplementedError` with a message pointing at this brief.

## Tasks

1. Add `set_credentials(node_id, username, password)` to `Firefox__Service`.
2. Add `upload_mitm_script(node_id, script_content)` to `Firefox__Service`.
3. Add routes `PUT /api/specs/firefox/{node_id}/credentials` and `PUT /api/specs/firefox/{node_id}/mitm-script` to `Routes__Firefox__Stack`.
4. Remove `NotImplementedError` from `Cli__Firefox.set_credentials` + `Cli__Firefox.upload_mitm_script`; wire them to call the HTTP API client (or the service directly via CLI-mode).
5. Tests — at minimum: route parses correctly, returns expected schema.

## Acceptance criteria

- `sg-compute spec firefox set-credentials --node <id> --username u --password p` reaches the service without `NotImplementedError`.
- `sg-compute spec firefox upload-mitm-script --node <id> --file /path` reads the file and uploads it.

## Source

Filed by T2.2 implementation as explicit PARTIAL deferral.
