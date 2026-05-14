# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Routes__Vault_Publish
# FastAPI route surface. Pure delegation to Publish__Service — no logic here.
#
# Endpoints (mounted at /vault-publish):
#   POST   /register             → Schema__VaultPublish__Register__Response
#   DELETE /unpublish/{slug}      → Schema__VaultPublish__Unpublish__Response
#   GET    /status/{slug}         → Schema__VaultPublish__Status__Response
#   POST   /wake                  → Schema__VaultPublish__Wake__Response  (always 200)
#   POST   /resolve               → Schema__VaultPublish__Resolve__Response
#   GET    /list                  → Schema__VaultPublish__List__Response
#   GET    /health                → Schema__VaultPublish__Health__Response
#
# The waker Lambda runs this same app and calls POST /wake.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                 import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                              import Fast_API__Routes

from vault_publish.schemas.Enum__Publish__Error_Code                         import Enum__Publish__Error_Code
from vault_publish.schemas.Schema__VaultPublish__Register__Request           import Schema__VaultPublish__Register__Request
from vault_publish.schemas.Schema__VaultPublish__Resolve__Request            import Schema__VaultPublish__Resolve__Request
from vault_publish.schemas.Schema__VaultPublish__Wake__Request               import Schema__VaultPublish__Wake__Request
from vault_publish.service.Publish__Service                                  import Publish__Service

# error-code value → HTTP status. Slug-validation errors (Enum__Slug__Error_Code)
# all map to 400; the orchestrator errors carry their own status.
_STATUS_FOR_ERROR = {
    Enum__Publish__Error_Code.SLUG_TAKEN.value      : 409,
    Enum__Publish__Error_Code.NOT_REGISTERED.value  : 404,
    Enum__Publish__Error_Code.VAULT_NOT_FOUND.value : 404,
}


def _raise(error_code) -> None:
    code   = error_code.value
    status = _STATUS_FOR_ERROR.get(code, 400)                                # slug-validation errors → 400
    raise HTTPException(status_code=status, detail={'error_code': code})


class Routes__Vault_Publish(Fast_API__Routes):
    tag     : str             = 'vault-publish'
    prefix  : str             = '/vault-publish'
    service : Publish__Service

    def register(self, body: Schema__VaultPublish__Register__Request) -> dict:
        response, error = self.service.register(str(body.slug)                   ,
                                                str(body.owner_id)               ,
                                                str(body.signing_public_key_ref) )
        if error:
            _raise(error)
        return response.json()
    register.__route_path__ = '/register'

    def unpublish(self, slug: str) -> dict:
        response, error = self.service.unpublish(slug)
        if error:
            _raise(error)
        return response.json()
    unpublish.__route_path__ = '/unpublish/{slug}'

    def status(self, slug: str) -> dict:
        response, error = self.service.status(slug)
        if error:
            _raise(error)
        return response.json()
    status.__route_path__ = '/status/{slug}'

    def wake(self, body: Schema__VaultPublish__Wake__Request) -> dict:
        # wake never raises — the outcome enum carries any rejection reason, so
        # the waker can always decide warming-page vs proxy.
        return self.service.wake(str(body.slug)).json()
    wake.__route_path__ = '/wake'

    def resolve(self, body: Schema__VaultPublish__Resolve__Request) -> dict:
        response, error = self.service.resolve(str(body.slug))
        if error:
            _raise(error)
        return response.json()
    resolve.__route_path__ = '/resolve'

    def list_slugs(self) -> dict:
        return self.service.list().json()
    list_slugs.__route_path__ = '/list'

    def health(self) -> dict:
        return self.service.health().json()
    health.__route_path__ = '/health'

    def setup_routes(self):
        self.add_route_post  (self.register  )
        self.add_route_delete(self.unpublish )
        self.add_route_get   (self.status    )
        self.add_route_post  (self.wake      )
        self.add_route_post  (self.resolve   )
        self.add_route_get   (self.list_slugs)
        self.add_route_get   (self.health    )
