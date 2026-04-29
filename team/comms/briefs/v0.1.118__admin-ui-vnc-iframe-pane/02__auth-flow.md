# 02 — Auth flow

## Where the password lives

- `sp vnc create` returns the password in the create response, ONCE.
  ```
  operator-pwd : <password>   (returned once — stash it now)
  ```
- The EC2 holds only the bcrypt hash — there is no recovery API.
- Today's CLI workflow: operator stashes the password in a vault entry or
  env var.

For the admin UI:

- The Admin Dashboard already has a vault concept (top-right "key" badge
  in the screenshot — `86b226575882`). Persist the operator password there
  keyed by `stack_name` at create time, so the UI can later present it to
  the iframe pane without prompting again.
- If the password is missing (e.g. stack created via CLI), the iframe pane
  prompts the user once and stashes it for the session.

## How Basic auth gets to the iframe

Modern browsers **strip credentials from URLs of the form**
`https://operator:pwd@host/` to mitigate phishing. So the historical trick of
`<iframe src="https://operator:pwd@1.2.3.4/">` does NOT work in Chrome,
Edge, Firefox, or Safari.

**Two viable approaches** — pick one:

### Approach A — let the browser prompt (zero code, ugly UX)

Mount the iframe with no creds. The browser shows its own native HTTP Basic
auth dialog inside the iframe on first load. After the user enters the
creds once, the browser caches them per-origin for the session. Subsequent
panes / refreshes don't re-prompt.

Pros: nothing to build.
Cons: native dialog is jarring, looks like a bug, doesn't match the admin
UI styling.

### Approach B — pre-warm the auth via a top-level fetch (recommended)

Before mounting the iframe, the admin UI does a `fetch(viewer_url, {
credentials: 'include', headers: { Authorization: 'Basic ' +
btoa('operator:'+pwd) } })`. The browser caches the auth for the origin.
Then mount the iframe with no creds — the cached auth is reused.

Pros: no native dialog; the admin UI controls the prompt and styling.
Cons: requires the password be available client-side (already true via
the vault).

Implementation note: the `fetch` MUST be cross-origin (admin UI vs
`{public_ip}`). Use `mode: 'cors'`. nginx will respond with the auth
challenge but as long as the `Authorization` header is included on the
fetch, the auth gets cached on the browser side regardless of CORS
preflight outcome.

## Tearing down auth on stack delete

When a stack is deleted, the EC2 is gone but the browser still has the
basic-auth cache. There is no "logout" endpoint. Acceptable: the cached
creds are scoped to the public IP, which is released back to AWS and
won't be reused for our stacks for a long time.
