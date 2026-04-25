# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda handler
# Entrypoint for running the SP CLI FastAPI app on AWS Lambda.
#
#   sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler
#
# Two boot paths, selected by env at cold-start:
#
#   • Agentic    — AGENTIC_APP_NAME is set. Routes through Agentic_Boot_Shim
#                  which downloads the pinned S3 zip, prepends to sys.path,
#                  then imports Fast_API__SP__CLI from the (potentially fresh)
#                  on-disk copy. Code-only deploys hot-swap via the shim.
#   • Baseline   — AGENTIC_APP_NAME unset. Boots Fast_API__SP__CLI directly
#                  from the baked image. Always-available rollback path.
#
# Uvicorn / local dev does not use this file — it instantiates
# Fast_API__SP__CLI directly.
#
# AWS_DEFAULT_REGION bridge
# ─────────────────────────
# Lambda auto-populates AWS_REGION based on the deployment region, but NOT
# AWS_DEFAULT_REGION — the latter is a reserved env var the user code cannot
# set. osbot-aws's AWS_Config.aws_session_region_name() reads
# AWS_DEFAULT_REGION with a hardcoded eu-west-1 fallback; without the bridge
# below, a eu-west-2 Lambda would talk to eu-west-1 endpoints. Executed at
# module import, before any boto3 client is created.
#
# ASCII-only on executable lines
# ──────────────────────────────
# When Lambda Init fails, awslambdaric posts the traceback (including the
# source line being executed) back to the runtime API. http.client encodes
# the body as latin-1, so any non-ASCII character on a line that ends up in
# a traceback will crash the bootstrap with UnicodeEncodeError, masking the
# real init error. Header comment blocks (like this one) are safe — they
# never appear in tracebacks. Inline comments on executable lines are not.
# ═══════════════════════════════════════════════════════════════════════════════

import os

os.environ.setdefault('AWS_DEFAULT_REGION', os.environ.get('AWS_REGION', ''))       # Bridge: see module header. ASCII-only on this line - if init fails, awslambdaric POSTs the source line back as latin-1 and U+2014 em-dashes crash the bootstrap.


SP_CLI_FAST_API_CLASS_PATH = 'sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI.Fast_API__SP__CLI'
SP_CLI_SERVICE_LABEL       = 'SP CLI service'
ENV_VAR__AGENTIC_APP_NAME  = 'AGENTIC_APP_NAME'                                     # Presence = agentic mode; absence = baseline


def is_agentic_mode() -> bool:
    return bool(os.environ.get(ENV_VAR__AGENTIC_APP_NAME))


def boot_via_shim():                                                                # Agentic path: Agentic_Code_Loader pulls the S3 zip, then Fast_API__SP__CLI imports from the extracted copy. ASCII-only inline comment - see line 31 note.
    from sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim import Agentic_Boot_Shim
    shim = Agentic_Boot_Shim(fast_api_class_path = SP_CLI_FAST_API_CLASS_PATH ,
                             service_label       = SP_CLI_SERVICE_LABEL        )
    error, handler_inner, _app, _code_source = shim.boot()
    if error:
        raise RuntimeError(error)                                                   # Surfaces in CloudWatch; Lambda treats as Init failure
    return handler_inner


def boot_baseline():                                                                # Baseline path: direct import from baked image; no S3, no shim. ASCII-only inline comment.
    from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI import Fast_API__SP__CLI
    return Fast_API__SP__CLI().setup().handler()


handler = boot_via_shim() if is_agentic_mode() else boot_baseline()                 # Module-level: cold-start cost paid once per container. ASCII-only inline comment.
