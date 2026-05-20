# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — Fast_API__Admin
# Serverless__Fast_API app for the admin control plane. Mangum-backed (handler()
# from the base), Swagger at /docs, root-mounted Routes__Admin.
#
# Auth: a cookie/header gate (Admin__Auth__Middleware) added in setup_middlewares.
# config.enable_api_key = False — admin uses the cookie gate, NOT the stock
# X-API-Key middleware.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API import Serverless__Fast_API

from sg_compute_specs.vault_publish.lambdas.admin.admin__config           import (
    ADMIN__FAST_API__TITLE, ADMIN__FAST_API__DESC)
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Service          import Admin__Service
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth__Middleware import Admin__Auth__Middleware
from sg_compute_specs.vault_publish.lambdas.admin.routes.Routes__Admin    import Routes__Admin


class Fast_API__Admin(Serverless__Fast_API):
    admin_service : Admin__Service = None

    def setup(self):
        with self.config as _:
            _.name           = ADMIN__FAST_API__TITLE
            _.description    = ADMIN__FAST_API__DESC
            _.enable_api_key = False                                                 # cookie gate instead of X-API-Key
        if self.admin_service is None:
            self.admin_service = Admin__Service()
        return super().setup()

    def setup_middlewares(self):
        super().setup_middlewares()                                                  # CORS + request-id from the base
        self.app().add_middleware(Admin__Auth__Middleware)                           # cookie/header gate + redirect-to-login

    def setup_routes(self):
        self.add_routes(Routes__Admin, admin_service=self.admin_service)
