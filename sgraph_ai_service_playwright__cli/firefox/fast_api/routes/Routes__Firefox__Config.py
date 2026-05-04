# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Firefox__Config
# Configuration sub-routes for a running Firefox stack. Pure delegation to
# Firefox__Service; no logic in this class.
#
# Endpoints (all under /firefox/{stack_id}/...)
# ────────────────────────────────────────────────────────────────────────────
#   3.1 Credentials
#       GET    /firefox/{stack_id}/credentials
#       PUT    /firefox/{stack_id}/credentials
#   3.2 MITM proxy
#       GET    /firefox/{stack_id}/mitm/status
#       GET    /firefox/{stack_id}/mitm/url
#   3.3 Security
#       GET    /firefox/{stack_id}/security
#       PUT    /firefox/{stack_id}/security
#   3.4 Profile
#       GET    /firefox/{stack_id}/profile
#       PUT    /firefox/{stack_id}/profile/start_url
#       PUT    /firefox/{stack_id}/profile/load
#   3.5 Health
#       GET    /firefox/{stack_id}/health
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Credentials__Update import Schema__Firefox__Credentials__Update
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Profile__Load       import Schema__Firefox__Profile__Load
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Security            import Schema__Firefox__Security
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Start_Url__Update   import Schema__Firefox__Start_Url__Update
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service                     import Firefox__Service, DEFAULT_REGION

TAG__ROUTES_FIREFOX_CONFIG = 'firefox'


class Routes__Firefox__Config(Fast_API__Routes):
    tag     : str             = TAG__ROUTES_FIREFOX_CONFIG
    service : Firefox__Service

    # ── 3.1 Credentials ─────────────────────────────────────────────────────

    def get_credentials(self, stack_id: str, region: str = '') -> dict:
        return self.service.get_credentials(region or DEFAULT_REGION, stack_id).json()
    get_credentials.__route_path__ = '/{stack_id}/credentials'

    def update_credentials(self, stack_id: str,
                           body: Schema__Firefox__Credentials__Update,
                           region: str = '') -> dict:
        self.service.update_credentials(region or DEFAULT_REGION, stack_id, body)
        return {}
    update_credentials.__route_path__ = '/{stack_id}/credentials'

    # ── 3.2 MITM proxy ──────────────────────────────────────────────────────

    def get_mitm_status(self, stack_id: str, region: str = '') -> dict:
        return self.service.get_mitm_status(region or DEFAULT_REGION, stack_id).json()
    get_mitm_status.__route_path__ = '/{stack_id}/mitm/status'

    def get_mitm_url(self, stack_id: str, region: str = '') -> dict:
        url = self.service.get_mitm_url(region or DEFAULT_REGION, stack_id)
        return {'stack_id': stack_id, 'mitmweb_url': url}
    get_mitm_url.__route_path__ = '/{stack_id}/mitm/url'

    # ── 3.3 Security toggles ────────────────────────────────────────────────

    def get_security(self, stack_id: str, region: str = '') -> dict:
        return self.service.get_security(region or DEFAULT_REGION, stack_id).json()
    get_security.__route_path__ = '/{stack_id}/security'

    def update_security(self, stack_id: str,
                        body: Schema__Firefox__Security,
                        region: str = '') -> dict:
        self.service.update_security(region or DEFAULT_REGION, stack_id, body)
        return {}
    update_security.__route_path__ = '/{stack_id}/security'

    # ── 3.4 Profile ─────────────────────────────────────────────────────────

    def get_profile(self, stack_id: str, region: str = '') -> dict:
        return self.service.get_profile(region or DEFAULT_REGION, stack_id).json()
    get_profile.__route_path__ = '/{stack_id}/profile'

    def update_start_url(self, stack_id: str,
                         body: Schema__Firefox__Start_Url__Update,
                         region: str = '') -> dict:
        self.service.update_start_url(region or DEFAULT_REGION, stack_id, str(body.url))
        return {}
    update_start_url.__route_path__ = '/{stack_id}/profile/start_url'

    def load_profile(self, stack_id: str,
                     body: Schema__Firefox__Profile__Load,
                     region: str = '') -> dict:
        self.service.load_profile(region or DEFAULT_REGION, stack_id, str(body.handle))
        return {}
    load_profile.__route_path__ = '/{stack_id}/profile/load'

    # ── 3.5 Detailed health ──────────────────────────────────────────────────

    def get_health(self, stack_id: str, region: str = '') -> dict:
        return self.service.get_detailed_health(region or DEFAULT_REGION, stack_id).json()
    get_health.__route_path__ = '/{stack_id}/health'

    def setup_routes(self):
        self.add_route_get (self.get_credentials  )
        self.add_route_put (self.update_credentials)
        self.add_route_get (self.get_mitm_status   )
        self.add_route_get (self.get_mitm_url      )
        self.add_route_get (self.get_security      )
        self.add_route_put (self.update_security   )
        self.add_route_get (self.get_profile       )
        self.add_route_put (self.update_start_url  )
        self.add_route_put (self.load_profile      )
        self.add_route_get (self.get_health        )
