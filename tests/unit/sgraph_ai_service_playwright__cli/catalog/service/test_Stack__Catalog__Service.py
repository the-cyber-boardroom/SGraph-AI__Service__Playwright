# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — fake service subclasses and fake registry for catalog tests (no AWS)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                  import Plugin__Registry
from sgraph_ai_service_playwright__cli.docker.collections.List__Schema__Docker__Info  import List__Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State        import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.plugin.Plugin__Manifest__Docker         import Plugin__Manifest__Docker
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info            import Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__List            import Schema__Docker__List
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service                 import Docker__Service
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.plugin.Plugin__Manifest__Elastic       import Plugin__Manifest__Elastic
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List          import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service               import Elastic__Service
from sgraph_ai_service_playwright__cli.linux.collections.List__Schema__Linux__Info    import List__Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State          import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.plugin.Plugin__Manifest__Linux           import Plugin__Manifest__Linux
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info              import Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__List              import Schema__Linux__List
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                   import Linux__Service
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info  import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State              import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.plugin.Plugin__Manifest__Vnc               import Plugin__Manifest__Vnc
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info           import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List           import Schema__Vnc__Stack__List
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                       import Vnc__Service


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


class _Fake_Vnc__Service(Vnc__Service):
    def list_stacks(self, region=None):
        stacks = List__Schema__Vnc__Stack__Info()
        stacks.append(Schema__Vnc__Stack__Info(stack_name='vnc-test', state=Enum__Vnc__Stack__State.RUNNING))
        return Schema__Vnc__Stack__List(stacks=stacks)


def _fake_registry() -> Plugin__Registry:
    registry = Plugin__Registry()
    registry.manifests['linux']   = Plugin__Manifest__Linux()
    registry.manifests['docker']  = Plugin__Manifest__Docker()
    registry.manifests['elastic'] = Plugin__Manifest__Elastic()
    registry.manifests['vnc']     = Plugin__Manifest__Vnc()
    registry.service_instances['linux']   = _Fake_Linux__Service()
    registry.service_instances['docker']  = _Fake_Docker__Service()
    registry.service_instances['elastic'] = _Fake_Elastic__Service()
    registry.service_instances['vnc']     = _Fake_Vnc__Service()
    return registry
