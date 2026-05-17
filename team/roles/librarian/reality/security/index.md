# security — Reality Index

**Domain:** `security/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** cross-cutting extraction from `.claude/CLAUDE.md` (rules 10-15) + the JS allowlist section of `_archive/v0.1.31/01__playwright-service.md` + the shell allowlist documented in `host-control/index.md`.

Cross-cutting AppSec rules that apply across every domain: JS expression allowlist, shell-command allowlist, vault-key hygiene, AWS naming constraints, no-credentials-in-git. None of these have a single "owner" package — they are constraints every contributor honours.

---

## EXISTS (code-verified)

### Rule 10 — `evaluate` action allowlist

**Codebase:** `JS__Expression__Allowlist` inside the Playwright service (see [`playwright-service/index.md`](../playwright-service/index.md)).

The Playwright `evaluate` action is **allowlist-gated**. Default = deny-all. The allowlist is enforced both at schema level (rejecting requests with disallowed expressions before they reach `Step__Executor`) and at execution time (double-check).

Widening the allowlist requires Architect / AppSec sign-off — every entry is a step closer to arbitrary code execution and must be justified by a real use case.

### Rule 11 — No arbitrary code execution

The shell-server pattern from OSBot-Playwright is **not** carried forward into this service. There is no `eval`-like surface anywhere in `Playwright__Service` or `Step__Executor` outside the gated JS allowlist.

### Shell command allowlist (host-control)

`sg_compute/host_plane/shell/shell_command_allowlist.py` — `SHELL_COMMAND_ALLOWLIST: list[str]` (deny-all default):

```
docker ps, docker logs, docker stats, docker inspect,
podman ps, podman logs, podman stats, podman inspect,
df -h, free -m, uptime, uname -r,
cat /proc/meminfo, cat /proc/cpuinfo,
systemctl status
```

Shared between `Safe_Str__Shell__Command` (schema-level rejection) and `Shell__Executor` (runtime double-check). New entries widen the gate — Architect / AppSec sign-off required.

The `WS /shell/stream` endpoint bypasses the allowlist because `rbash` itself is the security boundary. See [`host-control/index.md`](../host-control/index.md).

### Rule 12 — No AWS credentials in git

**Where they live:** GH Actions repository secrets only.

**Where they are NEVER allowed:**
- `.env.example`
- Any committed file in the repo

The `.env.example` template uses placeholder values; the runtime `.env` is gitignored.

### Rule 13 — No vault keys in git

Vault keys (e.g. `sgit` dev-pack key) are shared **out-of-band**. If one appears in a diff, **block the commit**.

The dev pack is mirrored from vault into `library/` on 2026-04-17 (see `.claude/CLAUDE.md`). Re-sync uses `sgit clone {VAULT_KEY} /tmp/playwright-dev-pack` — the key is never committed.

### Rule 14 — Security group `GroupName` must NOT start with `sg-`

AWS reserves the `sg-*` prefix for security group IDs and rejects `CreateSecurityGroup` with `InvalidParameterValue` if `GroupName` matches.

**Tracked precedent:**
- `scripts/provision_ec2.py:83` — `SG__NAME = 'playwright-ec2'`.
- `sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py` — `sg_name_for_stack` helper enforces `-sg` suffix; never `sg-` prefix.
- Now generalised via `aws/Stack__Naming.py` — `Stack__Naming(section_prefix='…').sg_name_for_stack(name)` is the canonical helper for every sister section. See [`cli/duality.md`](../cli/duality.md).

### Rule 15 — AWS `Name` tag must never double-prefix

When the logical name already carries the namespace (e.g. `elastic-quiet-fermi`), do not wrap it again into `elastic-elastic-quiet-fermi`. Use `aws_name_for_stack` (prefixes only when missing) — defined in `Stack__Naming` for every sister section.

---

### CLAUDE.md cross-cutting rules summary

For context, the full list of non-negotiable security rules from `.claude/CLAUDE.md`:

| Rule # | Topic | Where enforced |
|--------|-------|----------------|
| 10 | Evaluate action allowlist-gated | `JS__Expression__Allowlist` (Playwright service) |
| 11 | No arbitrary code execution / no shell-server pattern | Cross-cutting; no module ships such a surface |
| 12 | No AWS credentials in git | Commit-time discipline + GH secrets |
| 13 | No vault keys in git | Commit-time discipline; shared out-of-band |
| 14 | SG `GroupName` not `sg-*` prefix | `Stack__Naming.sg_name_for_stack` |
| 15 | AWS `Name` tag — no double-prefix | `Stack__Naming.aws_name_for_stack` |

### Mutation env-var gates (cross-cutting)

| Env var | What it unlocks | Source |
|---------|-----------------|--------|
| `SG_AWS__DNS__ALLOW_MUTATIONS=1` | `sg aws dns records update` + `sg aws dns records delete` | [`cli/aws-dns.md`](../cli/aws-dns.md) |
| `SG_AWS__CF__ALLOW_MUTATIONS=1` | `sg vp bootstrap` CloudFront distribution creation; `sg aws cf` mutations | [`sg-compute/index.md`](../sg-compute/index.md) (v0.2.23) |

`records add` and `instance create-record` use confirmation prompts only (no env-var gate) because adds are additive + ephemeral.

### Audit log (mitmproxy)

`agent_mitmproxy/addons/audit_log_addon.py` emits NDJSON to stdout on every response with `Proxy-Authorization` decoded so the proxy user is surfaced. See [`agent-mitmproxy/index.md`](../agent-mitmproxy/index.md).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources: `.claude/CLAUDE.md` (rules 10-15); [`_archive/v0.1.31/01__playwright-service.md`](../_archive/v0.1.31/01__playwright-service.md); [`host-control/index.md`](../host-control/index.md) (shell allowlist)
- Playwright JS allowlist: [`playwright-service/index.md`](../playwright-service/index.md)
- Host-control RBAC / shell hardening proposals: [`host-control/proposed/index.md`](../host-control/proposed/index.md)
- DNS mutation gates: [`cli/aws-dns.md`](../cli/aws-dns.md)
