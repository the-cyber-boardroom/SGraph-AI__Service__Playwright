# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — _Fake_Elastic__Service + _client helper for Routes__Elastic__Stack tests
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
from osbot_fast_api.api.Fast_API import Fast_API
from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Health__Check import List__Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status           import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.fast_api.routes.Routes__Elastic__Stack import Routes__Elastic__Stack
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Response import Schema__Elastic__Create__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Delete__Response import Schema__Elastic__Delete__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Check    import Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Response import Schema__Elastic__Health__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List        import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service

STACK_NAME  = 'elastic-quiet-fermi'
INSTANCE_ID = 'i-0123456789abcdef0'


class _Fake_Elastic__Service(Elastic__Service):
    def __init__(self, hit: bool = True):
        super().__init__()
        self.hit             = hit
        self.last_create_req : Optional[Schema__Elastic__Create__Request] = None

    def list_stacks(self, region=None):
        stacks = List__Schema__Elastic__Info()
        if self.hit:
            stacks.append(Schema__Elastic__Info(stack_name=STACK_NAME, instance_id=INSTANCE_ID,
                                                 region='eu-west-2', state=Enum__Elastic__State.RUNNING))
        return Schema__Elastic__List(region=region or 'eu-west-2', stacks=stacks)

    def get_stack_info(self, stack_name=None, region=None):
        if not self.hit:
            return None
        return Schema__Elastic__Info(stack_name=STACK_NAME, instance_id=INSTANCE_ID,
                                      region='eu-west-2', state=Enum__Elastic__State.RUNNING)

    def create(self, request):
        self.last_create_req = request
        return Schema__Elastic__Create__Response(stack_name=STACK_NAME, instance_id=INSTANCE_ID,
                                                  region='eu-west-2', elastic_password='Test-Pass-0000-0000',
                                                  state=Enum__Elastic__State.PENDING)

    def delete_stack(self, stack_name=None, region=None):
        if not self.hit:
            return Schema__Elastic__Delete__Response(stack_name=stack_name or '')
        ids = List__Instance__Id()
        ids.append(INSTANCE_ID)
        return Schema__Elastic__Delete__Response(stack_name=stack_name or STACK_NAME,
                                                  target=INSTANCE_ID, terminated_instance_ids=ids)

    def health(self, stack_name=None, password='', check_ssm=True):
        checks = List__Schema__Elastic__Health__Check()
        checks.append(Schema__Elastic__Health__Check(name='tcp-443', status=Enum__Health__Status.OK))
        return Schema__Elastic__Health__Response(stack_name=stack_name or STACK_NAME,
                                                  all_ok=True, checks=checks)


def _client(service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Elastic__Stack, service=service)
    return app.client()
