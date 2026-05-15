# DevOps Brief

The infrastructure in this pack is "provision once, then forget" — except for two
things that must be monitored. This document is for the DevOps role.

---

## 1. The one-time wildcard setup

All of this is done **once** and rarely touched again. All AWS calls go through
`osbot-aws` (`.claude/CLAUDE.md` #14) — no raw `boto3`.

### 1.1 Route 53

- Confirm / create the hosted zone for `sgraph.app`.
- One ALIAS/A record per environment wildcard, all pointing at the single
  CloudFront distribution: `*.sgraph.app`, `*.qa.sgraph.app`, `*.dev.sgraph.app`,
  `*.main.sgraph.app`.

### 1.2 ACM

- One wildcard certificate, **issued in `us-east-1`** (CloudFront requires its
  certs there regardless of where the rest of the stack lives).
- SANs = the four environment wildcards above. ACM's default SAN limit is 10 —
  ample for the env set; if region wildcards are added later, request an increase.
- **DNS-validated** against the Route 53 zone — leave the validation `CNAME`
  records in the zone permanently (see §2.1).

### 1.3 CloudFront

- One distribution. Alternate domain names = the four wildcards.
- Attach the ACM cert.
- Phase 1: a single dynamic origin resolution to the per-slug EC2 (VPC origin).
- Phase 2a: origin = the waker Lambda Function URL.
- Phase 2b: origin group (primary = per-slug EC2 VPC origin, secondary = waker
  Lambda); **tune the origin connection timeout down to ~2 s with 1 attempt** — the
  30 s default makes cold-path failover unacceptably slow.
- Warming-page responses must be served `no-cache`; Phase 2b custom error
  responses get a low TTL (a few seconds).

### 1.4 VPC

- A private subnet for the per-slug EC2 instances — no public IPv4, no IGW route on
  the runtime path.
- CloudFront VPC origin configuration so the distribution can reach the private
  instances (Phase 2b) — and/or the waker Lambda placed in the VPC so it can proxy
  to / provision the private instances (Phase 2a).
- Security groups: per-slug instances egress only to the SG/API path and
  CloudFront; no instance-to-instance reachability.

---

## 2. The two things that must be monitored

Most of this infra is fire-and-forget. These two are not.

### 2.1 ACM auto-renewal

ACM auto-renews DNS-validated certificates **only while the validation `CNAME`
records remain in the hosted zone**. If someone cleans up "unused" DNS records, the
next renewal silently fails and every `*.sgraph.app` site goes dark when the cert
expires. Action: leave the validation records in place permanently, and add a
CloudWatch alarm on the certificate's `DaysToExpiry`.

### 2.2 The waker Lambda

It is on the cold-request path for every slug. Monitor its error rate and duration.
A waker that is failing means every cold vault fails to come up — and because warm
vaults stop themselves on idle, "every vault is cold" is the steady state overnight.

---

## 3. CloudFormation vs Terraform

The upstream brief flagged this as a research item. Recommendation: **use whatever
this team already uses for the rest of the AWS estate** — the wildcard setup is
small, one-time, and rarely changed, so the deciding factor is "what can the team
operate without friction", not the tooling's capabilities. Do not introduce a
second IaC tool for this one stack. Document the setup as code in the chosen tool
and check it in.

The per-slug EC2 lifecycle is **not** IaC — instances are created, started,
stopped, and terminated dynamically by `Instance__Manager` via `osbot-aws`. Only
the once-provisioned layer (zone, cert, distribution, subnet, security groups) is
IaC.

---

## 4. The waker Lambda packaging

The waker is the `vault_publish` FastAPI app behind the AWS Lambda Web Adapter —
the **same single-image model** the repo already uses for `lambda_handler.py`.
DevOps work:

- Build the image with the `vault_publish` app importable without side effects.
- Deploy as a Lambda with a Function URL.
- The narrow documented `boto3` exception for the Lambda Function URL
  two-statement permission fix (per `.claude/CLAUDE.md` #14) applies here if
  needed — nowhere else.

---

## 5. CI

- The `vault_publish` test suite runs in the existing GitHub Actions pipeline
  (x86_64), no mocks, no patches — in-memory composition only.
- Deploy-via-pytest for the waker Lambda and the routing: numbered tests
  (`test_1__...`, `test_2__...`) that provision, invoke, and assert against the
  real distribution, gated to skip cleanly when AWS credentials are absent — the
  same pattern as the existing deploy tests.
- No AWS credentials in Git — GitHub Actions repository secrets only
  (`.claude/CLAUDE.md` #12).
