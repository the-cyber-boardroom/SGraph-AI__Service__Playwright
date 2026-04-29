# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Stack__Catalog
# Two read-only endpoints: type catalog + cross-section stack list.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service


class Routes__Stack__Catalog(Fast_API__Routes):
    tag     : str                  = 'catalog'
    service : Stack__Catalog__Service

    def types(self) -> dict:
        return self.service.get_catalog().json()
    types.__route_path__ = '/types'

    def stacks(self) -> dict:
        return self.service.list_all_stacks().json()
    stacks.__route_path__ = '/stacks'

    def setup_routes(self):
        self.add_route_get(self.types )
        self.add_route_get(self.stacks)
