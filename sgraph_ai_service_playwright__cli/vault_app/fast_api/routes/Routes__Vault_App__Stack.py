# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Vault_App__Stack
# HTTP surface for the sp vault-app section. Routes carry zero logic —
# they delegate to Vault_App__Service and serialise the Type_Safe response.
#
# Endpoints
# ─────────
#   POST   /vault-app/stack                    -> Schema__Vault_App__Stack__Create__Response
#   GET    /vault-app/stacks                   -> Schema__Vault_App__Stack__List
#   GET    /vault-app/stack/{name}             -> Schema__Vault_App__Stack__Info (404 on miss)
#   DELETE /vault-app/stack/{name}             -> Schema__Vault_App__Stack__Delete__Response (404 on miss)
#   GET    /vault-app/stack/{name}/health      -> Schema__Vault_App__Health
#   POST   /vault-app/stack/{name}/seed        -> dict (seed result per key)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Create__Request \
                                                                                    import Schema__Vault_App__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Service         import DEFAULT_REGION, Vault_App__Service


TAG__ROUTES_VAULT_APP = 'vault-app'


class Routes__Vault_App__Stack(Fast_API__Routes):
    tag     : str                = TAG__ROUTES_VAULT_APP
    service : Vault_App__Service                                                    # Injected by Fast_API__SP__CLI.setup_routes()

    def list_stacks(self, region: str = '') -> dict:                                # GET /vault-app/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /vault-app/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no vault-app stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /vault-app/stack
        request = Schema__Vault_App__Stack__Create__Request.from_json(body)
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /vault-app/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.terminated_instance_ids:
            raise HTTPException(status_code=404, detail=f'no vault-app stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '') -> dict:                          # GET /vault-app/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name).json()
    health.__route_path__ = '/stack/{name}/health'

    def seed(self, name: str, keys: str = '', region: str = '') -> dict:            # POST /vault-app/stack/{name}/seed
        return self.service.seed_vault(region or DEFAULT_REGION, name, keys)
    seed.__route_path__ = '/stack/{name}/seed'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
        self.add_route_post  (self.seed       )
