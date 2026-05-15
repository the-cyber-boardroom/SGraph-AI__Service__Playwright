# Appendix A — Glossary

Every term used in this pack, defined once.

| Term | Definition |
|------|------------|
| **ACM** | AWS Certificate Manager. Issues and auto-renews the wildcard TLS certificate. CloudFront requires its certs in `us-east-1`. |
| **Allowlisted vocabulary** | The closed set of operations `Manifest__Interpreter` will act on. Anything outside it is rejected, never passed through. Deny-by-default, like the JS expression allowlist. |
| **Billing record** | The only per-slug state. Already exists (slug validation was introduced for billing). Carries slug → owner binding and the signing public key reference. The integrity anchor. |
| **Control-plane** | The FastAPI service this repo already adds to every instance it creates. The waker drives provisioning through it. |
| **Control-plane key** | A random, single-use, per-instance secret the waker generates and delivers via IMDSv2 to authenticate to the control-plane during the setup window. |
| **CloudFront VPC origin** | A CloudFront feature that lets the distribution reach an EC2/ALB in a private subnet with no public IP. |
| **Derivation** | The deterministic, server-side function `slug → (Transfer-ID, read key)`, reusing SG/Send's simple-token mechanism. Replaces the routing KV. |
| **IMDSv2** | EC2 Instance Metadata Service v2. The channel for delivering the single-use control-plane key to an instance — never a CloudFront-facing channel. |
| **Lambda Web Adapter** | The AWS component that lets a normal HTTP app (FastAPI) run inside a Lambda. The repo's existing single-image model uses it; the waker reuses it. |
| **Origin failover / origin group** | A CloudFront feature: a primary origin and a secondary origin; CloudFront fails over to the secondary on connection failure or 5xx. The Phase 2b wake mechanism. |
| **Per-slug instance** | One EC2 per slug, in a private subnet, no public IP. Generic AMI; pulls vault content at boot; arms an idle-shutdown timer. |
| **Provisioning manifest** | The declarative document inside the vault folder that configures the instance. Signature-verified before use; interpreted against the allowlisted vocabulary. |
| **Reserved slugs** | The maintained, versioned set of slug names that cannot be registered (`www`, `api`, `admin`, …). A registry, not an inline list. |
| **`send.sgraph.ai`** | The SG/Send surface from which the waker fetches published vault folders. The MVP vault source. |
| **`sgit publish`** | The SG/Send CLI command an end user runs to publish a vault. Lives in the SG/Send repo — a *client* of the `vault-publish` API, not part of this repo. |
| **`sg vp`** | The operator/admin CLI verb tree in *this* repo: `register`, `unpublish`, `status`, `wake`, `resolve`, `list`, `health`. |
| **Simple token** | SG/Send's existing mechanism for resolving an opaque identifier to a Transfer-ID + read key. The slug derivation reuses it. |
| **Single-label wildcard** | A DNS/ACM wildcard matches exactly one label: `*.sgraph.app` covers `slug.sgraph.app` but not `slug.qa.sgraph.app`. Every environment and region needs its own wildcard. |
| **Slim-AMI principle** | From `SPEC-slim-ami-s3-nvme`: an EBS snapshot carrying large data pays a lazy-load tax on every launch, so it carries none — large data is pulled at boot. Per-slug instances inherit this by pulling vault content at boot. |
| **Slug** | A human-chosen subdomain label, e.g. `sara-cv` in `sara-cv.sgraph.app`. |
| **Transfer-ID** | The SG/API identifier for a vault transfer. Derived from the slug, used with the read key to fetch the vault folder. |
| **Vault folder** | The immutable file/folder fetched from SG/API by `(Transfer-ID, read key)`. Contains the site content and the provisioning manifest. |
| **Waker** | The small Lambda — the `vault_publish` FastAPI app behind the Lambda Web Adapter — that CloudFront uses as its dynamic/failover origin. Starts the instance, provisions it, serves the warming page. |
| **Warming page** | The auto-refreshing HTML page the waker returns while an instance boots. A polling page, not an HTTP redirect; served `no-cache`. |
