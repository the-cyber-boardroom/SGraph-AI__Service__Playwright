# ═══════════════════════════════════════════════════════════════════════════════
# Waker — lambda_entry
# Boots Fast_API__Waker under uvicorn for AWS Lambda Web Adapter (LWA).
# LWA binary (injected via extension layer) proxies Lambda HTTP events to
# uvicorn on port 8080 — no Mangum wrapper needed.
#
# _app is module-level so tests can introspect routes without calling run().
# run() is only called when the module is used as the Lambda entry point.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

sys.path.append('/opt/python')                                                     # LWA workaround — preserve layer path on cold start

from sg_compute_specs.vault_publish.waker.Fast_API__Waker import Fast_API__Waker

_fast_api = Fast_API__Waker().setup()
_app      = _fast_api.app()


def run():
    import uvicorn
    uvicorn.run(_app, host='0.0.0.0', port=8080)


if __name__ == '__main__':
    run()
