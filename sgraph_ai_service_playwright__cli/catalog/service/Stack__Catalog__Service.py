# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Stack__Catalog__Service
# Composes per-section services. Owns the static catalog and the cross-section
# stack list.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Type__Catalog__Entry import List__Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Summary             import List__Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type                              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary                       import Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary__List                 import Schema__Stack__Summary__List
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog                 import Schema__Stack__Type__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service__Entries             import Stack__Catalog__Service__Entries
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service                               import Docker__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service                             import Elastic__Service
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                                 import Linux__Service
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                                     import Vnc__Service


class Stack__Catalog__Service(Stack__Catalog__Service__Entries):
    linux_service   : Linux__Service
    docker_service  : Docker__Service
    elastic_service : Elastic__Service
    vnc_service     : Vnc__Service

    def get_catalog(self) -> Schema__Stack__Type__Catalog:
        entries = List__Schema__Stack__Type__Catalog__Entry()
        for method in (self.entry__linux, self.entry__docker, self.entry__elastic,
                       self.entry__opensearch, self.entry__vnc):
            entries.append(method())
        return Schema__Stack__Type__Catalog(entries=entries)

    def list_all_stacks(self, type_filter: Enum__Stack__Type = None) -> Schema__Stack__Summary__List:
        summaries = List__Schema__Stack__Summary()
        LINUX   = Enum__Stack__Type.LINUX
        DOCKER  = Enum__Stack__Type.DOCKER
        ELASTIC = Enum__Stack__Type.ELASTIC
        if type_filter in (None, LINUX):
            for info in self.linux_service.list_stacks('').stacks:
                summaries.append(Schema__Stack__Summary(
                    type_id=LINUX, stack_name=str(info.stack_name),
                    state=info.state.value, public_ip=str(info.public_ip),
                    region=str(info.region), instance_id=str(info.instance_id),
                    uptime_seconds=info.uptime_seconds))
        if type_filter in (None, DOCKER):
            for info in self.docker_service.list_stacks('').stacks:
                summaries.append(Schema__Stack__Summary(
                    type_id=DOCKER, stack_name=str(info.stack_name),
                    state=info.state.value, public_ip=str(info.public_ip),
                    region=str(info.region), instance_id=str(info.instance_id),
                    uptime_seconds=info.uptime_seconds))
        if type_filter in (None, ELASTIC):
            for info in self.elastic_service.list_stacks().stacks:
                summaries.append(Schema__Stack__Summary(
                    type_id=ELASTIC, stack_name=str(info.stack_name),
                    state=info.state.value, public_ip=str(info.public_ip),
                    region=str(info.region), instance_id=str(info.instance_id),
                    uptime_seconds=info.uptime_seconds))
        VNC = Enum__Stack__Type.VNC
        if type_filter in (None, VNC):
            for info in self.vnc_service.list_stacks('').stacks:
                summaries.append(Schema__Stack__Summary(
                    type_id=VNC, stack_name=str(info.stack_name),
                    state=info.state.value, public_ip=str(info.public_ip),
                    region=str(info.region), instance_id=str(info.instance_id),
                    uptime_seconds=info.uptime_seconds))
        return Schema__Stack__Summary__List(stacks=summaries)
