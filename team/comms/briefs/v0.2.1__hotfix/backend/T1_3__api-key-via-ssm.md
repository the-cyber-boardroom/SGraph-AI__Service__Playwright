# T1.3 — API key via SSM, not plaintext in EC2 user-data

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.1, T1.2, T1.4-T1.6).

## What's wrong

`Section__Sidecar` bakes the sidecar API key as **plaintext** into the EC2 user-data script (e.g. `docker run -e FAST_API__AUTH__API_KEY__VALUE=abc123...`).

EC2 user-data is **readable from inside the instance** via the Instance Metadata Service (IMDS) at `http://169.254.169.254/latest/user-data`. **Any process running on the Node — including any pod — can exfiltrate the sidecar's API key** with one HTTP GET.

## Why it matters

Combined with T1.4 (`POST /api/nodes` empty key) and T1.5 (single-key Pod__Manager): a captured key from one pod ≈ root-equivalent access to **every Node in the fleet** (the same env-var key is used everywhere per current Pod__Manager design).

## Tasks

The brief's intent (per `architecture/03__sidecar-contract.md`) is that the API key reaches the sidecar via a path that an inside-the-instance attacker cannot read. Two options; pick with Architect:

### Option A — SSM Parameter Store (recommended)

1. Generate a per-Node random API key in `EC2__Platform.create_node` (a `secrets.token_urlsafe(32)` or osbot-aws equivalent).
2. Write it to SSM as a `SecureString` at `/sg-compute/nodes/{node_id}/sidecar-api-key`.
3. EC2 IAM role gets `ssm:GetParameter` permission scoped to `/sg-compute/nodes/*`.
4. `Section__Sidecar` user-data fetches the value at boot via `aws ssm get-parameter --with-decryption` (uses the IAM role; not via IMDS user-data).
5. Store the SSM path on `Schema__Node__Info.host_api_key_vault_path` so `Pod__Manager` can read it back (T1.5 will use this).

### Option B — Vault (if vault is available at boot time)

Same shape, vault instead of SSM. Pre-requires T2.4 (real vault writer); blocks this hotfix on Tier 2 — not preferred.

### Recommended: Option A.

## Tasks (Option A)

1. Create `sg_compute/platforms/ec2/secrets/SSM__Sidecar__Key.py` — `Type_Safe` wrapper for write/read/delete via osbot-aws.
2. Update `EC2__Platform.create_node` — generate a per-Node key, write to SSM, embed the SSM path (not the value) into user-data.
3. Update `Section__Sidecar.render(...)` — replace plaintext-key parameter with an SSM-path parameter; render `aws ssm get-parameter ... > /tmp/api_key && export FAST_API__AUTH__API_KEY__VALUE=$(cat /tmp/api_key)` in the bash.
4. Update IAM policy attached by `Ec2__Service` (`__cli/ec2/`) — add `ssm:GetParameter` on `/sg-compute/nodes/*`.
5. Update `Schema__Node__Info` — add `host_api_key_vault_path : Safe_Str__SSM__Path` (or rename to `host_api_key_ssm_path`).
6. Tests: assert no plaintext key appears in the rendered user-data.

## Acceptance criteria

- `grep "FAST_API__AUTH__API_KEY__VALUE=[a-zA-Z0-9]" $(find . -name "Section__Sidecar*")` returns zero hits.
- `Schema__Node__Info` carries `host_api_key_ssm_path` (or vault path).
- `EC2__Platform.create_node` writes the key to SSM and embeds only the path.
- Sidecar still boots and authenticates.
- IAM policy scoped to `/sg-compute/nodes/*`, not `*`.

## "Stop and surface" check

If you find IAM-permission limitations preventing SSM access from inside the EC2: **STOP**. The Node's IAM role is in your `Ec2__Service` config — adjust there. Do not fall back to plaintext.

## Live smoke test

Boot a Node; `curl http://169.254.169.254/latest/user-data` from the sidecar → expect to see the SSM path, **not** the API key value. `aws ssm get-parameter --name /sg-compute/nodes/{node_id}/sidecar-api-key --with-decryption` from the sidecar → expect 200 with the key.

## Source

Executive review T1.3; backend-early review §"Top 2 + 3 (combined)".
