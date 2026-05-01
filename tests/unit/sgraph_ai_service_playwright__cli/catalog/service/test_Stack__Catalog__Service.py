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
from sgraph_ai_service_playwright__cli.podman.collections.List__Schema__Podman__Info  import List__Schema__Podman__Info
from sgraph_ai_service_playwright__cli.podman.enums.Enum__Podman__Stack__State        import Enum__Podman__Stack__State
from sgraph_ai_service_playwright__cli.podman.plugin.Plugin__Manifest__Podman         import Plugin__Manifest__Podman
from sgraph_ai_service_playwright__cli.podman.schemas.Schema__Podman__Info            import Schema__Podman__Info
from sgraph_ai_service_playwright__cli.podman.schemas.Schema__Podman__List            import Schema__Podman__List
from sgraph_ai_service_playwright__cli.podman.service.Podman__Service                 import Podman__Service
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info  import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State              import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.plugin.Plugin__Manifest__Vnc               import Plugin__Manifest__Vnc
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info           import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List           import Schema__Vnc__Stack__List
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                       import Vnc__Service


class _Fake_Podman__Service(Podman__Service):
    def list_stacks(self, region=None):
        stacks = List__Schema__Podman__Info()
        stacks.append(Schema__Podman__Info(stack_name='podman-test', state=Enum__Podman__Stack__State.RUNNING))
        return Schema__Podman__List(stacks=stacks)


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
    registry.manifests['podman']  = Plugin__Manifest__Podman()
    registry.manifests['docker']  = Plugin__Manifest__Docker()
    registry.manifests['elastic'] = Plugin__Manifest__Elastic()
    registry.manifests['vnc']     = Plugin__Manifest__Vnc()
    registry.service_instances['podman']  = _Fake_Podman__Service()
    registry.service_instances['docker']  = _Fake_Docker__Service()
    registry.service_instances['elastic'] = _Fake_Elastic__Service()
    registry.service_instances['vnc']     = _Fake_Vnc__Service()
    return registry
