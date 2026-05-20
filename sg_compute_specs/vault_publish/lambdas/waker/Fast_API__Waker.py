# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish waker — Fast_API__Waker
# Serverless__Fast_API app for the edge router. Mangum-backed (handler() from
# the base), Swagger at /docs, root-mounted Routes__Waker.
#
# config.enable_api_key = False — the waker is public (slug routing must work
# for anonymous viewers). config.enable_cors = False — the base CORS middleware
# would emit allow_origins='*'; the waker's only CORS surface (/__waker__/probe)
# builds its own zone-matched headers, so the stock middleware is turned off.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API import Serverless__Fast_API

from sg_compute_specs.vault_publish.lambdas.waker.waker__config        import (
    WAKER__FAST_API__TITLE, WAKER__FAST_API__DESC)
from sg_compute_specs.vault_publish.lambdas.waker.routes.Routes__Waker import Routes__Waker


class Fast_API__Waker(Serverless__Fast_API):

    def setup(self):
        with self.config as _:
            _.name           = WAKER__FAST_API__TITLE
            _.description    = WAKER__FAST_API__DESC
            _.enable_api_key = False                                                 # public router — no X-API-Key gate
            _.enable_cors    = False                                                 # probe builds its own zone-matched CORS
        return super().setup()

    def setup_routes(self):
        self.add_routes(Routes__Waker)
