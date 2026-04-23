# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda handler
# Entrypoint for running the SP CLI FastAPI app on AWS Lambda via Mangum.
# Import this module (not a function) from the Lambda runtime handler setting:
#
#   sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler
#
# Uvicorn / local dev does not use this file — it instantiates
# Fast_API__SP__CLI directly.
# ═══════════════════════════════════════════════════════════════════════════════

from mangum                                                                         import Mangum

from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                   import Fast_API__SP__CLI


fast_api = Fast_API__SP__CLI().setup()                                              # Module-level init — cold-start cost paid once per container
app      = fast_api.app()
handler  = Mangum(app, lifespan='off')                                              # Lambda Web Adapter not required for the SP CLI app; Mangum is lighter
