---
title: "sg aws — Getting Started"
file: 01__getting-started.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 01 — Getting started

The five things you need to know before running any `sg aws *` command.

---

## 1. Credentials

`sg aws *` uses the standard AWS credential chain — same as the `aws` CLI:

1. `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+ optionally `AWS_SESSION_TOKEN`) in the environment
2. `AWS_PROFILE` pointing at a section in `~/.aws/credentials`
3. IMDS (when running on EC2)
4. AWS SSO via `aws sso login`

If nothing is configured the first AWS API call returns `NoCredentialsError`. Test with:

```bash
sg aws billing last-48h --top 3       # cheapest read-only call
```

---

## 2. Region

Most commands honour `AWS_REGION` (or `AWS_DEFAULT_REGION`). Override per-invocation:

```bash
AWS_REGION=us-west-2 sg aws cf distributions list
```

Region-special-cases:

| Command | Behaviour |
|---------|-----------|
| `sg aws acm list` | Dual-region by default — current region + `us-east-1` (CloudFront cert region). `--region R` forces single region. |
| `sg aws cf *` | CloudFront is **global** — region is mostly ignored by the API itself. |
| `sg aws iam *` | IAM is global. Region setting is irrelevant for IAM calls. |
| `sg aws lambda *` | Per-region. Functions in `us-east-1` won't show up if `AWS_REGION=eu-west-2`. |

---

## 3. Mutation gates

Mutation verbs refuse to run unless an env var is set:

```bash
sg aws dns records delete tmp.sgraph.ai
# → error: SG_AWS__DNS__ALLOW_MUTATIONS=1 required

SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records delete tmp.sgraph.ai --yes
# → deletes
```

The four gates:

| Gate | Covers |
|------|--------|
| `SG_AWS__DNS__ALLOW_MUTATIONS=1` | `dns records add/update/delete`, `dns zone purge`, `dns instance create-record` |
| `SG_AWS__CF__ALLOW_MUTATIONS=1` | `cf distribution create/disable/delete` |
| `SG_AWS__IAM__ALLOW_MUTATIONS=1` | `iam role create/delete`, `iam policy attach/detach` |
| `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` | `lambda <name> deploy/delete`, `lambda <name> url create/delete` |

Read-only verbs (`list`, `show`, `check`, `get`, `wait`, `details`, `config`, `logs`, `invocations`) never need a gate.

**Don't** export these env vars permanently in your shell rc. Set them inline for the one command, or in a short-lived shell:

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 SG_AWS__CF__ALLOW_MUTATIONS=1 bash
# … run a handful of commands …
exit
```

---

## 4. JSON output

Every command supports `--json`. Output is a single JSON value (object or array) suitable for `jq`:

```bash
sg aws lambda list --json | jq '.[] | .name'
sg aws billing week --json | jq '.totals'
sg aws dns zones list --json | jq '.[] | select(.name | test("sgraph"))'
```

Without `--json` you get a Rich-rendered table. The table view is for humans; the JSON view is for pipelines and scripting.

---

## 5. Confirmation prompts and `--dry-run`

Mutating verbs prompt `[y/N]` before they act. Two ways to skip the prompt:

```bash
# pass --yes (or -y)
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records delete tmp.sgraph.ai --yes

# pipe-friendly: pre-answer
yes | SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records delete tmp.sgraph.ai
```

A handful of commands support `--dry-run` — they print what they *would* do without making the AWS call. Always preferred for the first run of any mutation in a new environment:

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns zone purge --dry-run
```

---

## A working "first session" sequence

```bash
# 1. confirm credentials
sg aws billing last-48h --top 3

# 2. survey the account
sg aws dns zones list
sg aws cf distributions list
sg aws iam role list --prefix sg-
sg aws lambda list

# 3. pick a function, look at it
sg aws lambda waker info
sg aws lambda waker logs --since 30m

# 4. (optional) one careful mutation, with --dry-run first
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns zone purge --dry-run
```

You're now oriented. Pick the area page for the surface you want to work in:

- [Route 53 →](02__dns.md)
- [ACM →](03__acm.md)
- [Billing →](04__billing.md)
- [CloudFront →](05__cloudfront.md)
- [IAM →](06__iam.md)
- [Lambda →](07__lambda.md)
