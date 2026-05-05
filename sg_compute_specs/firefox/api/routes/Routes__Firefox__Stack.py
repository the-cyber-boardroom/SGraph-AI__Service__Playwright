# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Routes__Firefox__Stack
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Create__Request       import Schema__Firefox__Stack__Create__Request
from sg_compute_specs.firefox.service.Firefox__Service                              import DEFAULT_REGION, Firefox__Service


TAG__ROUTES_FIREFOX = 'firefox'


class Routes__Firefox__Stack(Fast_API__Routes):
    tag     : str             = TAG__ROUTES_FIREFOX
    service : Firefox__Service


    def list_stacks(self, region: str = '') -> dict:                                # GET /api/specs/firefox/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                            # GET /api/specs/firefox/stack/{name}
        result = self.service.get_stack_info(region or DEFAULT_REGION, name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no firefox stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: dict) -> dict:                                           # POST /api/specs/firefox/stack
        request = Schema__Firefox__Stack__Create__Request.from_json(body)           # body: dict avoids pydantic schema-generation for nested Schema__Firefox__Interceptor__Choice
        return self.service.create_stack(request).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                          # DELETE /api/specs/firefox/stack/{name}
        response = self.service.delete_stack(region or DEFAULT_REGION, name)
        if not response.deleted and not response.target:
            raise HTTPException(status_code=404, detail=f'no firefox stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str, region: str = '', timeout_sec: int = 0) -> dict:   # GET /api/specs/firefox/stack/{name}/health
        return self.service.health(region or DEFAULT_REGION, name, timeout_sec=timeout_sec).json()
    health.__route_path__ = '/stack/{name}/health'

    def set_credentials(self, node_id: str, body: dict) -> dict:                   # PUT /api/specs/firefox/{node_id}/credentials
        region   = body.get('region'  , '') or DEFAULT_REGION
        username = body.get('username', '')
        password = body.get('password', '')
        if not username or not password:
            raise HTTPException(status_code=422, detail='username and password are required')
        return self.service.set_credentials(region, node_id, username, password).json()
    set_credentials.__route_path__ = '/{node_id}/credentials'

    def upload_mitm_script(self, node_id: str, body: dict) -> dict:               # PUT /api/specs/firefox/{node_id}/mitm-script
        region  = body.get('region' , '') or DEFAULT_REGION
        content = body.get('content', '')
        if not content:
            raise HTTPException(status_code=422, detail='content is required')
        return self.service.upload_mitm_script(region, node_id, content).json()
    upload_mitm_script.__route_path__ = '/{node_id}/mitm-script'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks      )
        self.add_route_get   (self.info             )
        self.add_route_post  (self.create           )
        self.add_route_delete(self.delete           )
        self.add_route_get   (self.health           )
        self.add_route_put   (self.set_credentials  )
        self.add_route_put   (self.upload_mitm_script)
