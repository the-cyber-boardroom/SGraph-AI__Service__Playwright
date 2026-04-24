# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda handler
# Entrypoint for running the SP CLI FastAPI app on AWS Lambda via Mangum.
# Import this module (not a function) from the Lambda runtime handler setting:
#
#   sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler
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
# ═══════════════════════════════════════════════════════════════════════════════

import os

os.environ.setdefault('AWS_DEFAULT_REGION', os.environ.get('AWS_REGION', ''))       # Bridge — see module header

from mangum                                                                         import Mangum

from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                   import Fast_API__SP__CLI


fast_api = Fast_API__SP__CLI().setup()                                              # Module-level init — cold-start cost paid once per container
app      = fast_api.app()
handler  = Mangum(app, lifespan='off')                                              # Lambda Web Adapter not required for the SP CLI app; Mangum is lighter
