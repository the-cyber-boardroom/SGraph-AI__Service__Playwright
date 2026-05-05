# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — lambda_handler
# Boots Fast_API__Host__Control under uvicorn for AWS Lambda Web Adapter (LWA).
# LWA binary proxies Lambda HTTP events to uvicorn on port 8000.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

sys.path.append('/opt/python')                                               # LWA workaround — preserve layer path on cold start

from sg_compute.host_plane.fast_api.Fast_API__Host__Control import Fast_API__Host__Control

_fast_api = Fast_API__Host__Control().setup()
_app      = _fast_api.app()


def run():
    import uvicorn
    uvicorn.run(_app, host='0.0.0.0', port=8000)


if __name__ == '__main__':
    run()
