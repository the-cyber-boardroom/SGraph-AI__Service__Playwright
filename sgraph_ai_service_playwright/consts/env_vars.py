# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Environment Variable Names (spec §7)
#
# Every env var is read via get_env(ENV_VAR__NAME) — never os.environ.get().
# Keeps the set of recognised env vars grep-able from one module.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Boot loader ──────────────────────────────────────────────────────────────
ENV_VAR__CODE_S3_BUCKET                = 'SG_PLAYWRIGHT__CODE_S3_BUCKET'
ENV_VAR__CODE_S3_KEY                   = 'SG_PLAYWRIGHT__CODE_S3_KEY'
ENV_VAR__CODE_VAULT_REF                = 'SG_PLAYWRIGHT__CODE_VAULT_REF'            # Alternative to S3

# ── Service auth ─────────────────────────────────────────────────────────────
ENV_VAR__ACCESS_TOKEN_HEADER           = 'SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER'
ENV_VAR__ACCESS_TOKEN_VALUE            = 'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'

# ── Vault integration ────────────────────────────────────────────────────────
ENV_VAR__SG_SEND_BASE_URL              = 'SG_PLAYWRIGHT__SG_SEND_BASE_URL'
ENV_VAR__SG_SEND_VAULT_KEY             = 'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'         # Bootstrap key for default vault

# ── Browser defaults ─────────────────────────────────────────────────────────
ENV_VAR__DEFAULT_HEADLESS              = 'SG_PLAYWRIGHT__DEFAULT_HEADLESS'
ENV_VAR__DEFAULT_PROXY_URL             = 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL'
ENV_VAR__IGNORE_HTTPS_ERRORS           = 'SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS'       # For TLS-intercepting proxies
ENV_VAR__CHROMIUM_EXECUTABLE           = 'SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE'       # Override path to Chromium binary (sandbox / custom Chrome / laptop)

# ── Deployment target detection ──────────────────────────────────────────────
ENV_VAR__DEPLOYMENT_TARGET             = 'SG_PLAYWRIGHT__DEPLOYMENT_TARGET'         # Explicit override
ENV_VAR__AWS_LAMBDA_RUNTIME_API        = 'AWS_LAMBDA_RUNTIME_API'                   # Set by Lambda; auto-detect
ENV_VAR__CI                            = 'CI'                                       # Set by GH Actions
ENV_VAR__CLAUDE_SESSION                = 'CLAUDE_SESSION'                           # Proposed: set in Claude envs

# ── Default artefact destinations ────────────────────────────────────────────
ENV_VAR__DEFAULT_S3_BUCKET             = 'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'
ENV_VAR__DEFAULT_LOCAL_ARTEFACT_FOLDER = 'SG_PLAYWRIGHT__DEFAULT_LOCAL_ARTEFACT_FOLDER'

# ── Reliability / watchdog ───────────────────────────────────────────────────
# AWS Lambda has no external way to kill a stuck invocation. If the main
# thread deadlocks (Playwright sync-inside-asyncio, hung proxy CONNECT, etc.)
# the container keeps billing until the Lambda lifetime expires. The request
# deadline + watchdog give us two layers of defence:
#   - REQUEST_DEADLINE_MS — soft per-request wall clock inside Sequence__Runner.
#     Between steps we check the deadline; remaining steps are marked SKIPPED
#     and the session is torn down. Can't interrupt a blocked page.goto()
#     (only Playwright's own timeout does that), but guarantees cleanup once
#     the current step returns.
#   - WATCHDOG_MAX_REQUEST_MS — hard cap enforced by a background daemon
#     thread. If ANY in-flight request exceeds this (even if the main thread
#     is fully deadlocked), the watchdog calls os._exit(2). LWA sees the
#     process die, AWS recycles the execution environment, next invocation
#     gets a fresh container. Works even when the main thread can't run.
#   - WATCHDOG_POLL_INTERVAL_MS — how often the watchdog thread wakes to check.
#   - WATCHDOG_DISABLED — '1' to disable (laptop dev, tests that need longer).
ENV_VAR__REQUEST_DEADLINE_MS           = 'SG_PLAYWRIGHT__REQUEST_DEADLINE_MS'
ENV_VAR__WATCHDOG_MAX_REQUEST_MS       = 'SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS'
ENV_VAR__WATCHDOG_POLL_INTERVAL_MS     = 'SG_PLAYWRIGHT__WATCHDOG_POLL_INTERVAL_MS'
ENV_VAR__WATCHDOG_DISABLED             = 'SG_PLAYWRIGHT__WATCHDOG_DISABLED'
