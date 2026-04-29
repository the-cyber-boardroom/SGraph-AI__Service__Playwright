# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — fake service subclasses for catalog tests (no AWS)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.docker.collections.List__Schema__Docker__Info import List__Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State      import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info          import Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__List          import Schema__Docker__List
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service               import Docker__Service
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List        import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.linux.collections.List__Schema__Linux__Info  import List__Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info            import Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__List            import Schema__Linux__List
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import Linux__Service


class _Fake_Linux__Service(Linux__Service):
    def list_stacks(self, region=None):
        stacks = List__Schema__Linux__Info()
        stacks.append(Schema__Linux__Info(stack_name='linux-test', state=Enum__Linux__Stack__State.RUNNING))
        return Schema__Linux__List(stacks=stacks)


class _Fake_Docker__Service(Docker__Service):
    def list_stacks(self, region=None):
        stacks = List__Schema__Docker__Info()
        stacks.append(Schema__Docker__Info(stack_name='docker-test', state=Enum__Docker__Stack__State.RUNNING))
        return Schema__Docker__List(stacks=stacks)


class _Fake_Elastic__Service(Elastic__Service):
    def list_stacks(self, region=None):                                             # elastic returns empty in this fixture
        stacks = List__Schema__Elastic__Info()
        return Schema__Elastic__List(stacks=stacks)
