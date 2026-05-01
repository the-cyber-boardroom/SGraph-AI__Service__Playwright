# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Stack__Catalog__Service
# Drives the type catalog and cross-section stack list from the plugin registry.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Type__Catalog__Entry import List__Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Summary             import List__Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary                       import Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary__List                 import Schema__Stack__Summary__List
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog                 import Schema__Stack__Type__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service__Entries             import Stack__Catalog__Service__Entries
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                                 import Plugin__Registry


class Stack__Catalog__Service(Stack__Catalog__Service__Entries):
    plugin_registry : Plugin__Registry

    def get_catalog(self) -> Schema__Stack__Type__Catalog:
        entries = List__Schema__Stack__Type__Catalog__Entry()
        for method in (self.entry__docker, self.entry__podman, self.entry__elastic,
                       self.entry__opensearch, self.entry__vnc):
            entries.append(method())
        return Schema__Stack__Type__Catalog(entries=entries)

    def list_all_stacks(self) -> Schema__Stack__Summary__List:
        summaries = List__Schema__Stack__Summary()
        for name, manifest in self.plugin_registry.manifests.items():
            type_id = manifest.catalog_entry().type_id
            svc     = self.plugin_registry.service_for(name)
            for info in svc.list_stacks('').stacks:
                summaries.append(Schema__Stack__Summary(
                    type_id        = type_id                ,
                    stack_name     = str(info.stack_name)   ,
                    state          = info.state.value       ,
                    public_ip      = str(info.public_ip)    ,
                    region         = str(info.region)       ,
                    instance_id    = str(info.instance_id)  ,
                    uptime_seconds = info.uptime_seconds    ))
        return Schema__Stack__Summary__List(stacks=summaries)
