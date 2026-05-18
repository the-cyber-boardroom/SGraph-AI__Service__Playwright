---
title: "02 — UX by state"
file: 02__ux-by-state.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 02 — UX by state

What the end-user sees at each state, with copy, mockups, and the
key UX questions that need answering.

The three categories of user:

- **Vault visitor** — the person who typed `https://sara-cv.aws.sg-labs.app`
  into a browser. Knows nothing about Lambda, CF, EC2.
- **Slug owner** — Sara. Cares about "is my vault up". Might know
  what an EC2 instance is.
- **Operator** — runs `sg vp …`. Cares about why something broke.

This file focuses on the visitor. Operator UX is in
[`04__cli-debug-commands.md`](04__cli-debug-commands.md).

---

## State 1 — Slug not registered (404)

**When:** Host header doesn't map to a known slug.

**Today:**
```
404 — Slug not found
No vault registered for this subdomain.
```

**The problem:** doesn't tell you what Host the Lambda actually saw.
If you hit the Lambda URL directly (debugging), you get this and
have no idea whether the issue is "missing CloudFront alias",
"wrong DNS", or "missing SSM entry".

**Proposed:**
```
404 — Vault not found

We can't find a vault registered for this subdomain.

Subdomain checked:  sara-cv.aws.sg-labs.app
Slug derived:       sara-cv
Zone:               aws.sg-labs.app

If you are the operator, register this slug with:
  sg vault-publish register sara-cv --vault-key <key>

Request ID: abcd-1234-…    (paste this when asking for help)
```

Light touch — adds the host the Lambda saw, the slug it tried to
look up, and the request ID for log correlation. No secrets, no
infrastructure leakage.

**Operator-only diagnostics** (gated on a `X-Waker-Debug: <token>`
header that matches a Lambda env var — never on by default):

```
404 — Vault not found

Subdomain checked:  sara-cv.aws.sg-labs.app
Slug derived:       sara-cv
Zone:               aws.sg-labs.app

DEBUG INFO (token-gated):
  SSM lookup       : not found at /sg-compute/vault-publish/slugs/sara-cv
  Registered slugs : alice-cv, bob-cv, taylor-cv
  Request ID       : abcd-1234-…
```

This is the difference between "shrug, file a ticket" and "oh,
typo — meant taylor-cv".

---

## State 2 — Slug registered, EC2 STOPPED (warming, 202)

**When:** SSM entry exists, EC2 found but stopped. Lambda has just
called `start_instances`.

**Today:**
```
[Spinner]
Vault is warming up

Slug: sara-cv
This page will refresh automatically every 10 seconds.
```

**The problem:** Sara has no idea what's happening. Is the page
going to come up in 30 s or 5 min? Did anything actually start?
Is she stuck in a refresh loop forever?

**Proposed:**
```
[Spinner]
Your vault is starting up

Slug:           sara-cv
What we're doing:  starting EC2 instance i-0abc1234
Started at:        10:01:23 UTC
Time elapsed:      14 seconds
Expected ready:    ~60 seconds from start

Auto-refreshes every 10s. You'll be taken straight to your vault
when it's ready.

If this page is still here after 3 minutes, something is wrong —
contact your operator with request ID: abcd-1234-…
```

The four numbers that matter:
- **What we're doing** — turns the mystery into a step.
- **Time elapsed** — answers "is it stuck?".
- **Expected ready** — sets an upper bound on the wait.
- **If still here after 3 min** — gives an escape hatch.

Time-elapsed requires the Lambda to know when the start was first
triggered. That state lives in SSM as `last_start_at` (new field on
the registry entry; written when STOPPED → start branch fires;
cleared when RUNNING+healthy detected).

---

## State 3 — EC2 PENDING or STOPPING (warming, 202)

**When:** AWS is mid-transition. Lambda doesn't re-call start.

**Today:** Same warming page as State 2. No distinction in copy.

**Proposed:** Same template, different "What we're doing":

- PENDING:  "EC2 instance is booting (state: pending)"
- STOPPING: "Previous shutdown is finishing (state: stopping). Will
  restart automatically when done."

Otherwise identical to State 2.

---

## State 4 — RUNNING but vault-app not healthy (warming, 200)

**When:** EC2 is up, but `urllib3` health probe to `:8080/ui/#!/login`
fails or returns 5xx. Vault-app stack is still booting / docker
compose hasn't finished pulling images / cert-init is mid-Let's-Encrypt
challenge.

**Today:** Same warming page.

**Proposed:** Same template, "What we're doing":

```
What we're doing:  waiting for the vault-app stack to become healthy
                   (EC2 is running; the vault server is still booting)
Health probe:      http://1.2.3.4:8080/ui/#!/login  →  no response
```

---

## State 5 — RUNNING + healthy (proxied response, 200)

**When:** Everything works. Lambda proxies the request to EC2.

**The proxy is invisible to the user** — they get the vault UI as if
they hit the EC2 directly. The only artefact of the proxy is in the
response headers:

```
X-Waker-State:        proxied
X-Waker-Slug:         sara-cv
X-Waker-Instance-Id:  i-0abc1234
X-Waker-Elapsed-Ms:   287
```

The vault UI loads. Sara sees her vault. Job done.

**Important UX detail:** even though the proxy works, the user URL
in their browser is still `sara-cv.aws.sg-labs.app` (CF preserves it).
After the per-slug DNS A record propagates (≤ 60 s TTL), refresh goes
direct to EC2 and Lambda exits the data path — same URL, same
appearance.

---

## State 6 — Proxy error (502)

**When:** EC2 is healthy per the probe, but the actual proxied
request fails (connection refused, timeout, response too large).

**Today:**
```
Proxy error: HTTPConnectionPool(...) Connection refused
```
or:
```
Response too large (12345678 bytes; cap is 5242880)
```

Plain text, 502 status code, no styling, no actionable info.

**Proposed:** styled HTML page matching the warming page aesthetic:

```
[Warning icon]
Vault server hiccup

Slug:        sara-cv
Error:       connection refused (EC2 went down between health-check
             and request)

Try refreshing in a few seconds. If this persists, contact your
operator with request ID: abcd-1234-…
```

Make it look like the warming page (same fonts, similar layout) so
the visual identity stays consistent. Auto-refresh after 5 s.

---

## State 7 — Response body too large (502, special case)

**When:** vault-app returns > 5 MB body (Lambda buffered cap is 6 MB;
we use 5 MB safety margin).

**Today:** plain-text 502.

**Proposed:**

```
Page too large to deliver via the waker

The vault page is bigger than 5 MB. The waker can only proxy responses
under that size — but the per-slug DNS record will be live in a few
seconds, after which your browser will hit the vault directly with no
size limit. Try refreshing.

Slug:         sara-cv
Page size:    12.3 MB
Cap:          5 MB (Lambda buffered response limit)
```

This is an edge case (most vault pages are well under 5 MB), but
when it hits, the visitor needs to know it's a known boundary, not
a broken vault.

---

## Cross-cutting UX rules

1. **Every page mentions the slug.** Visitor confirmation they're
   looking at the right vault.
2. **Every page includes the request ID.** Even if hidden in a
   collapsed `<details>` — operator-meaningful, user-ignorable.
3. **Every page is styled.** No raw `text/plain`. Same design
   language across all states (Inter-style font, light-grey
   background, no branding, looks like a system page).
4. **No spinning forever.** Every "wait" page has either an
   auto-refresh + expected-ready window or a clear escape hatch.
5. **No JavaScript.** All pages are static HTML with meta-refresh.
   Works in the most stripped-down browser, no XSS surface.
6. **No vault content leaks.** The warming/error pages never include
   anything from the vault (no slug-owner names, no vault-app
   strings). The slug name itself is OK — it's already in the URL.

## The single template

All states share one Jinja2-style HTML template (rendered with
`str.format()` to avoid the Jinja dep). Variables:

- `title`            — "Vault not found" / "Vault is warming up" / etc.
- `icon`             — spinner / warning / x / check
- `slug`             — always present
- `host`             — debug only
- `status_line`      — "What we're doing" copy
- `details_block`    — optional table of key:value rows
- `auto_refresh_s`   — 0 to disable
- `request_id`       — always present, in details

One template file, six states, consistent UX. Today's
`Warming__Page` becomes `Waker__Page` with a `state: Enum`
parameter and per-state copy from a typed dictionary.
