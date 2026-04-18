# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Environment Variable Names
#
# Every env var is read via get_env(ENV_VAR__NAME) — never os.environ.get().
# Keeps the set of recognised env vars grep-able from one module.
#
# Two prefixes:
#   • AGENTIC_*       — framework-level vars consumed by the generic boot shim
#                       and admin FastAPI (v0.1.29+). Destined for extraction
#                       into a shared package; do not namespace under the app.
#   • SG_PLAYWRIGHT__ — app-specific vars (auth tokens, vault, browser defaults,
#                       watchdog). Stay under the app namespace.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Agentic boot loader (v0.1.29 — generic S3-zip hot-swap) ──────────────────
# The lambda_entry.py shim reads these at container start to decide WHERE
# the Python code comes from. Precedence: CODE_LOCAL_PATH > S3 > passthrough.
ENV_VAR__AGENTIC_APP_NAME              = 'AGENTIC_APP_NAME'                         # Logical app name, e.g. 'sg-playwright'
ENV_VAR__AGENTIC_APP_STAGE             = 'AGENTIC_APP_STAGE'                        # 'dev' / 'main' / 'prod'
ENV_VAR__AGENTIC_APP_VERSION           = 'AGENTIC_APP_VERSION'                      # Pinned version to load, e.g. 'v0.1.29'
ENV_VAR__AGENTIC_CODE_LOCAL_PATH       = 'AGENTIC_CODE_LOCAL_PATH'                  # Override: use this local path instead of S3 (mounted volume)
ENV_VAR__AGENTIC_CODE_SOURCE           = 'AGENTIC_CODE_SOURCE'                      # Written by the boot shim; surfaced on /info — 's3:…', 'local:…', 'passthrough:sys.path'
ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET = 'AGENTIC_CODE_SOURCE_S3_BUCKET'            # Optional bucket override; default derives from '{account}--sgraph-ai--{region}'
ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    = 'AGENTIC_CODE_SOURCE_S3_KEY'               # Optional key override; default derives from 'apps/{name}/{stage}/{version}.zip'
ENV_VAR__AGENTIC_IMAGE_VERSION         = 'AGENTIC_IMAGE_VERSION'                    # Override for the baked image_version file (debugging only)
ENV_VAR__AGENTIC_ADMIN_MODE            = 'AGENTIC_ADMIN_MODE'                       # 'disabled' / 'read_only' / 'full'. Default 'read_only'; 'full' deferred.
ENV_VAR__AWS_REGION                    = 'AWS_REGION'                               # Set by Lambda automatically; absent on laptop

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
