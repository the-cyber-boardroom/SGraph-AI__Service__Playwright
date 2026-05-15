# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__TLS lambda_handler
# Container entrypoint for the slim TLS surface. Unlike the other handlers it
# launches through Fast_API__TLS__Launcher, so the same image serves plain HTTP
# (FAST_API__TLS__ENABLED unset) or HTTPS on :443 (enabled + cert sidecar ran).
#
#   python -m sg_compute.fast_api.tls.lambda_handler
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.fast_api.Fast_API__TLS__Launcher import Fast_API__TLS__Launcher
from sg_compute.fast_api.tls.Fast_API__TLS       import Fast_API__TLS

_fast_api = Fast_API__TLS().setup()
_app      = _fast_api.app()


def run():
    Fast_API__TLS__Launcher().serve(_app)


if __name__ == '__main__':
    run()
