# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Neko
# Neko is a WebRTC-based self-hosted browser (n.eko). Shipped as a stub with
# enabled=False pending the structured experiment (v0.23.x__neko-evaluation).
#
# env-override policy:
#   PLUGIN__NEKO__ENABLED=false  → registry skips (standard disable)
#   There is NO env-override to *enable* a manifest-disabled plugin. Setting
#   PLUGIN__NEKO__ENABLED=true does NOT mount Neko routes; it only prevents the
#   env-override-disabled path — the manifest.enabled=False check still applies.
#   To enable Neko for real, change enabled=True in this file (requires deploy).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.neko.fast_api.routes.Routes__Neko__Stack     import Routes__Neko__Stack
from sgraph_ai_service_playwright__cli.neko.service.Neko__Service                   import Neko__Service


class Plugin__Manifest__Neko(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('neko')
    display_name : str                     = 'Neko (WebRTC browser, experimental)'
    description  : str                     = 'n.eko self-hosted browser via WebRTC. Under evaluation — see neko/docs/README.md.'
    enabled      : bool                    = False                              # gated on experiment results; do NOT change without running evaluation
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL

    def service_class(self):
        return Neko__Service

    def routes_classes(self):
        return [Routes__Neko__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.NEKO,
            display_name          = self.display_name,
            description           = self.description,
            available             = False,                                      # SOON tile in UI until experiment completes
            default_instance_type = 't3.large',
            expected_boot_seconds = 120,
            create_endpoint_path  = '/neko/stack',
            list_endpoint_path    = '/neko/stacks',
            info_endpoint_path    = '/neko/stack/{name}',
            delete_endpoint_path  = '/neko/stack/{name}',
            health_endpoint_path  = '/neko/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['neko:stack.created', 'neko:stack.deleted']
