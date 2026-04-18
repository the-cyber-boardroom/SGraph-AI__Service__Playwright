# ═══════════════════════════════════════════════════════════════════════════════
# Agentic Lambda boot shim (v0.1.29 — generic S3-zip hot-swap)
#
# Lives INSIDE the container image (copied to /var/task/lambda_entry.py) and is
# the Lambda entry point. Resolves WHERE the Python code comes from BEFORE it
# imports the FastAPI service, so the same image can run three ways:
#
#   1. LAMBDA                       — AWS_REGION set, CODE_LOCAL_PATH unset →
#                                     download s3://<bucket>/<key>, extract to
#                                     /tmp, prepend to sys.path.
#   2. LOCAL DOCKER W/ MOUNT        — AGENTIC_CODE_LOCAL_PATH=/mnt/code (volume)
#                                     → skip S3, just prepend that directory.
#   3. PYTEST / UVICORN PASSTHROUGH — neither env var set → do nothing; use
#                                     whatever sys.path already has.
#
# Env var contract (all AGENTIC_* — destined to be generic):
#   • AGENTIC_CODE_LOCAL_PATH       — explicit local path, bypasses S3.
#   • AGENTIC_CODE_SOURCE_S3_BUCKET — optional; default {account}--sgraph-ai--{region}.
#   • AGENTIC_CODE_SOURCE_S3_KEY    — optional; default apps/{name}/{stage}/{version}.zip.
#   • AGENTIC_APP_NAME              — e.g. 'sg-playwright'.
#   • AGENTIC_APP_STAGE             — 'dev' / 'main' / 'prod'.
#   • AGENTIC_APP_VERSION           — 'v0.1.29'.
#   • AGENTIC_CODE_SOURCE           — written by the shim, surfaced on /info.
#   • AGENTIC_IMAGE_VERSION         — written by the shim from /var/task/image_version.
#
# No fallback service. A top-level try/catch pins `error`/`handler`/`app` — if
# setup fails inside Lambda, `run(event, ctx)` returns the critical error string
# as the response body and operators see it in CloudWatch + the client response.
# Outside Lambda, we re-raise so the stack trace lands in the dev loop.
#
# The boot shim is baked into the IMAGE on purpose (not the zip). It's the
# rollback escape hatch: if the zip is unloadable the image is still there.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys


IMAGE_VERSION_PATH                    = '/var/task/image_version'                   # Baked at build time by the Dockerfile
CODE_CACHE_ROOT                       = '/tmp/agentic-code'                         # Lambda's only writable scratch; persists across warm invocations
DEFAULT_BUCKET_FORMAT                 = '{account_id}--sgraph-ai--{region_name}'    # Matches scripts/deploy_code.py
DEFAULT_KEY_FORMAT                    = 'apps/{app_name}/{stage}/{version}.zip'     # Matches scripts/deploy_code.py

ENV_VAR__AGENTIC_APP_NAME             = 'AGENTIC_APP_NAME'
ENV_VAR__AGENTIC_APP_STAGE            = 'AGENTIC_APP_STAGE'
ENV_VAR__AGENTIC_APP_VERSION          = 'AGENTIC_APP_VERSION'
ENV_VAR__AGENTIC_CODE_LOCAL_PATH      = 'AGENTIC_CODE_LOCAL_PATH'
ENV_VAR__AGENTIC_CODE_SOURCE          = 'AGENTIC_CODE_SOURCE'
ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET = 'AGENTIC_CODE_SOURCE_S3_BUCKET'
ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY   = 'AGENTIC_CODE_SOURCE_S3_KEY'
ENV_VAR__AGENTIC_IMAGE_VERSION        = 'AGENTIC_IMAGE_VERSION'
ENV_VAR__AWS_REGION                   = 'AWS_REGION'
ENV_VAR__LAMBDA_FUNCTION              = 'AWS_LAMBDA_FUNCTION_NAME'


# ─── Stage 1: helpers (no side effects at import) ────────────────────────────

def read_image_version() -> str:                                                    # Best-effort — missing file means local dev / non-Lambda
    if os.path.exists(IMAGE_VERSION_PATH):
        with open(IMAGE_VERSION_PATH, 'r') as f:
            return f.read().strip()
    return 'v0'                                                                     # Matches Safe_Str__Version regex — "unknown / pre-v0.1.28"


def load_code_from_local_path():                                                    # AGENTIC_CODE_LOCAL_PATH wins over S3 — laptop dev + volume mounts
    local_path = os.environ.get(ENV_VAR__AGENTIC_CODE_LOCAL_PATH)
    if not local_path:
        return None
    if not os.path.isdir(local_path):
        raise RuntimeError(f'{ENV_VAR__AGENTIC_CODE_LOCAL_PATH} is not a directory: {local_path}')
    sys.path.insert(0, local_path)
    return f'local:{local_path}'


def resolve_s3_bucket(account_id: str, region_name: str) -> str:                    # Explicit override > computed default
    override = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET)
    if override:
        return override
    return DEFAULT_BUCKET_FORMAT.format(account_id=account_id, region_name=region_name)


def resolve_s3_key() -> str:                                                        # Explicit override > computed from app name / stage / version
    override = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY)
    if override:
        return override
    app_name = os.environ[ENV_VAR__AGENTIC_APP_NAME]
    stage    = os.environ[ENV_VAR__AGENTIC_APP_STAGE]
    version  = os.environ[ENV_VAR__AGENTIC_APP_VERSION]
    return DEFAULT_KEY_FORMAT.format(app_name=app_name, stage=stage, version=version)


def load_code_from_s3():                                                            # AWS_REGION gate — only runs inside Lambda
    if os.environ.get(ENV_VAR__AGENTIC_CODE_LOCAL_PATH):                            # Local override already handled
        return None
    if not os.environ.get(ENV_VAR__AWS_REGION):                                     # Not on Lambda
        return None

    import boto3, io, zipfile                                                       # Deferred imports — keep module-level import graph minimal

    region_name = os.environ[ENV_VAR__AWS_REGION]
    account_id  = boto3.client('sts').get_caller_identity()['Account']
    bucket_name = resolve_s3_bucket(account_id, region_name)
    s3_key      = resolve_s3_key()
    target_dir  = f'{CODE_CACHE_ROOT}/{bucket_name}/{s3_key}'

    if _cache_is_fresh(target_dir, bucket_name, s3_key):                            # Warm-invocation short-circuit — ~200 ms saved per hit
        sys.path.insert(0, target_dir)
        return f's3:{bucket_name}/{s3_key}→{target_dir} (cached)'

    os.makedirs(target_dir, exist_ok=True)
    response  = boto3.client('s3').get_object(Bucket=bucket_name, Key=s3_key)
    zip_bytes = response['Body'].read()
    etag      = response.get('ETag', '').strip('"')

    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    _write_cache_etag(target_dir, etag)
    sys.path.insert(0, target_dir)
    return f's3:{bucket_name}/{s3_key}→{target_dir}'


def _cache_is_fresh(target_dir: str, bucket_name: str, s3_key: str) -> bool:        # ETag comparison — if S3 object unchanged and cache exists, reuse
    etag_file = os.path.join(target_dir, '.etag')
    if not os.path.exists(etag_file):
        return False
    try:
        import boto3
        head    = boto3.client('s3').head_object(Bucket=bucket_name, Key=s3_key)
        current = head.get('ETag', '').strip('"')
        with open(etag_file, 'r') as f:
            cached = f.read().strip()
        return bool(current) and current == cached
    except Exception:                                                               # Any failure — just re-download; safer than a stale cache hit
        return False


def _write_cache_etag(target_dir: str, etag: str) -> None:
    if not etag:
        return
    with open(os.path.join(target_dir, '.etag'), 'w') as f:
        f.write(etag)


def resolve_code_source() -> str:                                                   # Precedence: local > S3 > passthrough. Returns a provenance string.
    return load_code_from_local_path() or load_code_from_s3() or 'passthrough:sys.path'


def boot():                                                                         # Stage 2+3 — import + setup; returns (error, handler, app, code_source)
    os.environ.setdefault(ENV_VAR__AGENTIC_IMAGE_VERSION, read_image_version())     # Surfaced in /health/info by Capability__Detector
    code_source = resolve_code_source()
    os.environ[ENV_VAR__AGENTIC_CODE_SOURCE] = code_source                          # Surfaced in /health/info — "s3:…", "local:…", or "passthrough:sys.path"

    try:
        from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service
        fa      = Fast_API__Playwright__Service().setup()
        handler = fa.handler()
        app     = fa.app()
        return None, handler, app, code_source
    except Exception as exc:
        if not os.environ.get(ENV_VAR__LAMBDA_FUNCTION):                            # Outside Lambda, stack trace > string — fail loud
            raise
        error = (f"CRITICAL ERROR: Failed to start Playwright service:\n\n"
                 f"{type(exc).__name__}: {exc}\n\n"
                 f"code_source: {code_source}")
        return error, None, None, code_source


# ─── Stage 2+3: execute ONLY when this file is the entry point ───────────────
#
# With Lambda Web Adapter the container CMD runs `python lambda_entry.py`, so
# __name__ == '__main__' and boot() fires. Tests that `import lambda_entry`
# get no side effects — they call helpers / boot() explicitly after scrubbing
# env.

error        = None
handler      = None
app          = None
code_source  = None


def main():                                                                         # Invoked by the Dockerfile CMD (and the __main__ block below)
    global error, handler, app, code_source
    error, handler, app, code_source = boot()
    if error:
        raise RuntimeError(error)
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))


def run(event, context=None):                                                       # Direct Lambda handler entry (non-LWA mode) — boots on first call
    global error, handler, app, code_source
    if handler is None and error is None:
        error, handler, app, code_source = boot()
    if error:
        return error
    return handler(event, context)


if __name__ == '__main__':
    main()
