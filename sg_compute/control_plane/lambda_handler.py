# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Control-Plane lambda_handler
# Boots Fast_API__Compute under uvicorn for AWS Lambda Web Adapter (LWA).
# LWA binary (injected via the extension layer) proxies Lambda HTTP events to
# uvicorn on port 8000 — no Mangum wrapper needed.
#
# _app is module-level so tests can introspect routes without calling run().
# run() is only called when the module is used as a Lambda entry point.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

sys.path.append('/opt/python')                                               # LWA workaround — preserve layer path on cold start

from sg_compute.control_plane.Fast_API__Compute import Fast_API__Compute

_fast_api = Fast_API__Compute().setup()
_app      = _fast_api.app()


def run():
    import uvicorn
    uvicorn.run(_app, host='0.0.0.0', port=8000)


if __name__ == '__main__':
    run()
