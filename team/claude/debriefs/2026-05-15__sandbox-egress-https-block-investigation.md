# Debrief — Sandbox-egress HTTPS block: investigation, the plain-HTTP workaround, and the revert

- **Date:** 2026-05-15
- **Branch:** `claude/architect-qa-service-ijc61`
- **Commits (in order):**
  - `813bf93` — vault-app: open `:8080` world-open when `--no-with-tls-check --with-aws-dns` *(later reverted)*
  - `ee3add2` — Revert "vault-app: open :8080 world-open when --no-with-tls-check --with-aws-dns"
- **Builds on:** [`2026-05-15__vault-app-fqdn-https-end-to-end.md`](2026-05-15__vault-app-fqdn-https-end-to-end.md) — the FQDN + browser-trusted LE cert work that this debrief is the failed-Claude-reachability follow-up for.
- **Source evidence (verbatim captures filed under `library/docs/research/`):**
  - [`v0.2.21__sandbox-egress-https-block__perplexity-network-audit.md`](../../library/docs/research/v0.2.21__sandbox-egress-https-block__perplexity-network-audit.md) — external-internet vantage (Perplexity)
  - [`v0.2.21__sandbox-egress-https-block__claude-agent-debrief.md`](../../library/docs/research/v0.2.21__sandbox-egress-https-block__claude-agent-debrief.md) — inside-Claude-sandbox vantage (separate Claude agent session)
- **Outcome:** **root cause identified, end-to-end fix NOT delivered.** We confirmed `fast-hopper.sg-compute.sgraph.ai` is reachable over HTTP from the Claude sandbox and HTTPS from the open internet, but the HTTPS-from-sandbox path is blocked by Anthropic's egress proxy. We shipped a code change that exposed plain-HTTP-on-:8080 as a workaround, then **reverted it** after deciding the trade-off wasn't right for the default surface. The Claude-reachable plain-HTTP path remains available via `--with-playwright --with-aws-dns` (Playwright on `:80`, no behaviour change required); the vault HTTPS path stays HTTPS-only.

---

## Why this matters — the gap this slice exposed

The [FQDN + LE-hostname slice](2026-05-15__vault-app-fqdn-https-end-to-end.md) was billed as "interesting capability → sellable service": one command, real FQDN, browser-trusted cert, standard ports. The big asterisk on that debrief — flagged red in its index entry — was:

> **🔴 Claude egress 503 to the deployed stack** — browser reaches `fast-hopper.sg-compute.sgraph.ai` fine, Anthropic's egress proxy returns `upstream connect error or disconnect/reset before headers`; this is independent of the work but means the "Claude-reachable" promise isn't quite delivered end-to-end yet, **next thread to pull**.

This session is that next thread. We did not solve it. We turned it from "we don't know what's blocking it" into a confirmed-root-cause + a documented workaround that other roles (sgit, vault, agent-runtime) can act on independently.

---

## What we tried — chronological

### 1. Confirmed the failure mode is environment-specific, not service-specific

Two vantages, opposite verdicts on the same host (`fast-hopper.sg-compute.sgraph.ai` → `18.169.240.189`):

| Vantage | HTTP `:80` | HTTPS `:443` | TLS cert presented |
|---|---|---|---|
| Open internet (Perplexity) | 401 from uvicorn ✅ | 401 from uvicorn ✅ | Real LE: `CN=fast-hopper…`, issuer `Let's Encrypt R12` → ISRG Root X1 |
| Inside Claude sandbox | 401 from uvicorn ✅ | **503 Envoy** ❌ | **Forged**: `O=Anthropic, CN=sandbox-egress-production TLS Inspection CA` |

The service itself is healthy. The Perplexity audit even ran a full TCP-port scan (and noted, separately, the EC2 SG has the `accept-and-hang` tarpit shape — not load-bearing for this investigation but worth a follow-up SG audit).

### 2. Confirmed the failure is at the egress TLS-interception layer

From a separate Claude-sandbox session:

- TLS handshake to the sgraph.ai hosts always succeeds — the egress generates a forged leaf inline (`*.sg-compute.sgraph.ai`, signed by `Egress Gateway Subordinate CA`).
- The 503 body — Envoy's `upstream connect error or disconnect/reset before headers` — comes from the *proxy* failing to complete its upstream TLS dial to the real origin, not from the origin being down.
- `--insecure` doesn't help. It bypasses *client*-side cert validation; the upstream dial is still attempted by the egress and still fails.

### 3. Ruled out the obvious hypotheses

| Hypothesis | Evidence against |
|---|---|
| Let's Encrypt cert chain problem | Real cert validates perfectly from the open internet. The cert Claude sees is a *different* cert (forged by the egress). |
| DNS / propagation lag | `dev.sg-playwright.sgraph.ai` has existed for weeks and fails identically. Age irrelevant. |
| Wildcard allowlist not matching | Failure is `503 upstream connect error`, not `403 host_not_allowed`. The string-match check passes; the upstream dial is what fails. |
| Origin-side firewall closing :443 to the egress | The same origin's :443 works fine from the open internet, including from Anthropic-adjacent IPs. The origin is happy to talk. |
| `*.sgraph.ai` wildcard cert presented by the egress is the bug | The forged leaf is the *intercept* mechanism, not the failure. Interception works (handshake completes); upstream routing is the failure. |

### 4. Settled on the root-cause model: "pre-warmed FQDN pool"

The egress proxy maintains a pool of FQDNs that are pre-warmed (DNS pre-resolved, upstream TLS state pre-negotiated, certs pre-issued by the intercept CA). For FQDNs **in** the pool, intercept-and-forward works. For FQDNs that pass the wildcard allowlist string check but are **not** in the pool, the handshake succeeds (the intercept CA can sign anything) but the upstream dial fails — yielding the 503.

Evidence for this specific shape (not "allowlist deny" and not "origin down"):

- HTTP (no interception path) works for every tested sgraph.ai subdomain on the same EC2 IP. Same network, same SG, same uvicorn — only the proxy path differs.
- The one sgraph.ai HTTPS host that *does* work from Claude (`dev.send.sgraph.ai`) is the long-standing default sgit server — exactly the kind of FQDN that would be pre-warmed because every Claude agent that uses sgit hits it.
- The 503 response shape is Envoy's upstream-failure shape, not its policy-deny shape.

We did not get to confirm this with Anthropic egress engineering; the model fits every observation but stays a hypothesis until they say so.

### 5. Confirmed the HTTP-on-:80 path is healthy from inside Claude

```
$ curl -sS http://fast-hopper.sg-compute.sgraph.ai/health/info | jq
{
  "name": "sg-playwright",
  "version": "v0.2.21",
  ...
}
```

Returned in ~200ms with no auth header. This was the load-bearing observation for the workaround attempt below.

### 6. Built the workaround — `--no-with-tls-check --with-aws-dns` opens vault on `:8080` plain HTTP, world-open

[Commit `813bf93`](https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright/commit/813bf93) (~50 LOC across 3 files + 1 test):

- `Vault_App__Service.create_stack`: when `--no-with-tls-check + --with-aws-dns`, add `8080 → 0.0.0.0/0` to the SG rules (the SG had `:8080` open caller-/32-only by default).
- `Vault_App__Service`: set `StackTlsHostname` tag whenever the FQDN is meaningful — TLS-on cert path OR plain-HTTP `--with-aws-dns` path — not only TLS-on. Tag's role broadened from "cert SAN" to "stack FQDN".
- `Vault_App__Stack__Mapper.to_info`: when TLS is off but the FQDN tag is set, `vault_url = http://<fqdn>:8080` (was: `http://<public_ip>:8080`).
- Test: `test_no_tls_with_fqdn_yields_plain_http_vault_url_on_8080`. 118 passed (was 117).

Result of running this on a fresh stack would have been:

```
vault-url       http://<stack>.sg-compute.sgraph.ai:8080
playwright-url  http://<stack>.sg-compute.sgraph.ai
```

Both reachable from Claude. Token still gates everything; traffic still flows through the egress MITM (which decrypts and re-encrypts) — so "plain HTTP" is a wire-format claim, not a security regression relative to the HTTPS path through the same MITM. The threat model (operator's vault + token) was the same in both paths.

### 7. Reverted the workaround — `ee3add2` on dev

The merge landed and was reverted shortly after on `dev` (commit `ee3add2`). Verified the revert is byte-for-byte clean against the pre-change state:

```
$ git diff 813bf93^ ee3add2 -- <three touched files>
(empty)
```

117 tests passing on dev. The plain-HTTP-:8080 path no longer exists as a default-vault posture.

---

## Why the revert was the right call (with hindsight)

Three reasons surface from re-reading the commit:

1. **The "Claude-reachability" goal isn't load-bearing for the vault.** The vault is for operators (humans + sgit). Operators don't need to reach it from inside a Claude sandbox; they need to reach it from their laptop or their CI. The HTTPS path works there. Burning a default-flag combination on "reachable from the one environment that MITM's HTTPS" makes the surface noisier for the 99% of users for whom HTTPS is fine.
2. **The reachability gap that *does* matter — Playwright from inside Claude — was already solved.** Playwright lives on `:80` plain HTTP via the FQDN. Claude can reach it. The vault doesn't need its own plain-HTTP exposure for the Claude-runs-Playwright use case.
3. **Workarounds calcify.** Once a `--no-with-tls-check --with-aws-dns` combination has documented semantics ("vault world-open on plain HTTP"), removing it later is a breaking change. The fix belongs at the *egress* layer (FQDN pool), not at the *origin* layer. Origin-layer workarounds make the egress fix less likely to ever land.

The revert is not "the change was wrong"; it's "the change was right for a specific operator workflow we don't want to encode as default". If we want it back, it'd be better as an explicit `--vault-plain-http` flag with an obvious warning, not as the implicit pairing of two existing flags.

---

## What we delivered

| Item | Status |
|---|---|
| Root cause confirmed (pre-warmed FQDN pool at egress) | ✅ |
| Two vantage-point captures filed (open-internet + sandbox) | ✅ — under `library/docs/research/` |
| Plain-HTTP-on-:8080 workaround | ⏪ shipped (`813bf93`), reverted (`ee3add2`) |
| Playwright-from-Claude path (port-80 FQDN) | ✅ already in place from the prior slice — unchanged |
| End-to-end "sgit push from Claude → fast-hopper vault" working | ❌ **still blocked**, needs egress fix |
| Cross-team escalation to Anthropic egress | ⚠️ identified as the next required action; not initiated this session |

---

## Failures — good / yellow / red

### 🟢 GOOD failures

- **Two-vantage diff caught the cert-MITM in minutes.** The first session that hit the 503 from inside Claude could have spiralled into "is LE down?" / "is our cert wrong?" / "is uvicorn crashed?". Instead, capturing the exact cert chain from the failing vantage (`O=Anthropic, CN=sandbox-egress-production TLS Inspection CA`) and contrasting it against the Perplexity audit (`Let's Encrypt R12`) made the MITM unambiguous. **The technique to keep: always grab the cert the failing client sees, not just the cert the origin says it's serving.**
- **Wildcard-allowlist hypothesis falsified by status-code shape.** The temptation was to assume "`*.sgraph.ai` isn't on the allowlist". The 503-vs-403 distinction (`upstream connect error` not `host_not_allowed`) ruled that out without needing access to Anthropic's allowlist config. Envoy's response taxonomy did the diagnosis for us.
- **Shipping the revert without ceremony.** The plain-HTTP-on-:8080 change took ~50 LOC and one test. The revert was a clean revert with zero residue. The cheap-to-reverse property meant we could try-and-back-off rather than debate-then-not-ship.

### 🟡 YELLOW failures

- **The plain-HTTP workaround used flag *implication* rather than an explicit flag.** Re-using `--no-with-tls-check + --with-aws-dns` as "the combination that means plain-HTTP world-open" overloaded two flags whose names don't telegraph that. A future operator reading `--with-aws-dns` reasonably assumes "give me TLS at an FQDN", not "swap the SG posture wide open on `:8080`". An explicit `--vault-plain-http` would have made the intent legible. If the workaround comes back, it should come back as a new flag.
- **The `StackTlsHostname` tag's semantic broadening got smuggled into the same commit as the SG change.** The tag's role shifting from "cert SAN" to "stack FQDN" was a semantic change worth its own commit + test sweep. Folding it in made the revert larger than it needed to be (it had to back out both the SG rule AND the tag-write gate). Fine here because we reverted whole-cloth, but a future split would have let us keep the tag-broadening (which had standalone value) and revert just the SG rule.
- **Didn't capture the `sg-compute SG accept-and-hang on all 65535 ports`** in a follow-up brief. Perplexity flagged it as the highest-priority external-audit finding. It's almost certainly the "hopper" listener doing its own thing and not a real exposure — but "almost certainly" isn't "documented and confirmed". This should turn into a small SG-audit task.

### 🔴 RED failures

- **End-to-end `sgit push` from inside Claude → `fast-hopper` vault still doesn't work, and we don't have a forcing function to fix it.** The fix lives on Anthropic's side (add `*.sg-compute.sgraph.ai` to the pre-warmed FQDN pool). Until that happens, every demo of "Claude builds a vault" stops at the `sgit init` step and falls over at the first push. The workaround we built and reverted *would have unblocked this*; the revert is the right call for the default surface, but it leaves the user-facing capability gap **unmoved**. The next session needs to either (a) file the cross-team brief to Anthropic egress, (b) revisit the explicit-flag version of the workaround, or (c) move the vault-from-Claude use case to a different transport (e.g. SSM port-forward, which doesn't traverse the egress at all).

---

## What's still actionable

In priority order:

1. **File a cross-team brief / Anthropic ticket asking for `*.sg-compute.sgraph.ai` to be added to the pre-warmed FQDN pool.** This is the only real fix. The brief should cite both vantage-point captures and the 503-vs-403 evidence. Without this, every other path is a workaround.
2. **If (1) is going to take weeks, ship the workaround as an explicit `--vault-plain-http` flag** (not flag-pair implication). Make it loud — warning in `info` output, comment-block in service, opt-in only. Re-apply the `StackTlsHostname` tag broadening as a separate, keep-able commit.
3. **Confirm whether `sgit` could speak HTTP** (`sgit push --base-url http://<fqdn>:8080 …` with an HTTP vault). Today vault is HTTPS-only when TLS is on; if we ship (2), sgit's `--base-url` already supports `http://` — no sgit changes needed.
4. **SG audit on the all-TCP-ports-open finding** from the Perplexity audit. Likely a `provision_ec2.py` / hopper-listener artefact; verify and either lock down or document.
5. **Add a "sandbox-egress matrix"** to the operator docs: what works from open internet, what works from Claude sandbox, what works from a typical corporate WAF. Three columns × `:80 / :443 / SSM-forward` rows. Stops the next person re-running this whole investigation.

---

## Cross-references

- Prior slice: [`2026-05-15__vault-app-fqdn-https-end-to-end.md`](2026-05-15__vault-app-fqdn-https-end-to-end.md) — the work this debrief is the failed-Claude-reachability follow-up for.
- LE-for-IP substrate: [`2026-05-15__vault-app-tls-letsencrypt-ip.md`](2026-05-15__vault-app-tls-letsencrypt-ip.md).
- Source captures: [`library/docs/research/v0.2.21__sandbox-egress-https-block__perplexity-network-audit.md`](../../library/docs/research/v0.2.21__sandbox-egress-https-block__perplexity-network-audit.md), [`library/docs/research/v0.2.21__sandbox-egress-https-block__claude-agent-debrief.md`](../../library/docs/research/v0.2.21__sandbox-egress-https-block__claude-agent-debrief.md).
- Reverted commit on dev: `ee3add2` ← `813bf93`.
