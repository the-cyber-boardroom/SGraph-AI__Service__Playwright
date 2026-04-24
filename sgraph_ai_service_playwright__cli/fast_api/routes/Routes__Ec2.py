# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Ec2
# Three endpoints for the EC2 instance lifecycle. Routes carry zero logic —
# they forward the request into Ec2__Service and serialise the Type_Safe
# response back to a dict.
#
#   POST   /ec2/instances              -> Schema__Ec2__Create__Response
#   GET    /ec2/instances/{target}     -> Schema__Ec2__Instance__Info
#   DELETE /ec2/instances/{target}     -> Schema__Ec2__Delete__Response
#
# The default path parser would derive GET /ec2/instances/{target} and
# DELETE /ec2/instances/{target} from two identically-named methods — not
# allowed in Python. The two mutating methods carry explicit __route_path__
# overrides so the parser is bypassed and both land on the same URL.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Request     import Schema__Ec2__Create__Request
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                     import Ec2__Service


TAG__ROUTES_EC2 = 'ec2'


class Routes__Ec2(Fast_API__Routes):
    tag     : str          = TAG__ROUTES_EC2
    service : Ec2__Service                                                          # Injected by Fast_API__SP__CLI.setup_routes()

    def instances(self, body: Schema__Ec2__Create__Request) -> dict:                # POST /ec2/instances
        return self.service.create(body).json()

    def get_instance(self, target: str) -> dict:                                    # GET /ec2/instances/{target}
        info = self.service.get_instance_info(target)
        if info is None:
            raise HTTPException(status_code=404, detail=f'no instance matched {target!r}')
        return info.json()
    get_instance.__route_path__ = '/instances/{target}'                             # Override the parser — give the route the canonical REST path

    def delete_instance(self, target: str) -> dict:                                 # DELETE /ec2/instances/{target}
        response = self.service.delete_instance(target)
        if not response.terminated_instance_ids:
            raise HTTPException(status_code=404, detail=f'no instance matched {target!r}')
        return response.json()
    delete_instance.__route_path__ = '/instances/{target}'                          # Same canonical path as GET, disambiguated by HTTP verb

    def setup_routes(self):
        self.add_route_post  (self.instances      )
        self.add_route_get   (self.get_instance   )
        self.add_route_delete(self.delete_instance)
