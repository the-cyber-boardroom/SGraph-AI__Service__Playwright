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

# ── Deployment target detection ──────────────────────────────────────────────
ENV_VAR__DEPLOYMENT_TARGET             = 'SG_PLAYWRIGHT__DEPLOYMENT_TARGET'         # Explicit override
ENV_VAR__AWS_LAMBDA_RUNTIME_API        = 'AWS_LAMBDA_RUNTIME_API'                   # Set by Lambda; auto-detect
ENV_VAR__CI                            = 'CI'                                       # Set by GH Actions
ENV_VAR__CLAUDE_SESSION                = 'CLAUDE_SESSION'                           # Proposed: set in Claude envs

# ── Default artefact destinations ────────────────────────────────────────────
ENV_VAR__DEFAULT_S3_BUCKET             = 'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'
ENV_VAR__DEFAULT_LOCAL_ARTEFACT_FOLDER = 'SG_PLAYWRIGHT__DEFAULT_LOCAL_ARTEFACT_FOLDER'
