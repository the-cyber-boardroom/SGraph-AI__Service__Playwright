# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Control-Plane lambda_handler
# Mangum wrapper around Fast_API__Compute for AWS Lambda + Lambda Web Adapter.
# Production runs under uvicorn; Lambda entry point is `handler`.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.control_plane.Fast_API__Compute import Fast_API__Compute

_fast_api = Fast_API__Compute().setup()
_app      = _fast_api.app()
handler   = None                                                            # Mangum wraps _app when installed; uvicorn uses _app directly

try:
    from mangum import Mangum
    handler = Mangum(_app)
except ImportError:
    pass
