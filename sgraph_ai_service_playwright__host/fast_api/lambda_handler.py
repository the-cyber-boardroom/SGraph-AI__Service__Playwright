# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — lambda_handler
# Mangum wrapper kept for local testing parity with the SP CLI pattern.
# Production entry point is uvicorn (see docker/host-control/Dockerfile).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__host.fast_api.Fast_API__Host__Control import Fast_API__Host__Control

_fast_api     = Fast_API__Host__Control().setup()
_app          = _fast_api.app()
handler       = None                                                        # Mangum wraps _app when installed; uvicorn uses _app directly

try:
    from mangum import Mangum
    handler = Mangum(_app)
except ImportError:
    pass
