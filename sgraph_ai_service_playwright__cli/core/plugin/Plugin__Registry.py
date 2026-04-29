# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Registry
# Discovers, loads, and exposes plugin manifests. The only place that imports
# plugin modules — everything else (Fast_API__SP__CLI, Stack__Catalog__Service)
# asks the registry instead of importing plugins directly.
#
# plugin_folders: explicit list of plugin names to discover. Default empty;
# callers set it from PLUGIN_FOLDERS (defined in this module) before calling
# discover(). Tests can set a custom list without touching production config.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from importlib                                                                  import import_module

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                import event_bus
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base       import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Plugin__Event \
                                                                                import Schema__Plugin__Event


# ── canonical plugin list — add a line here when a new plugin folder lands ──
PLUGIN_FOLDERS: list = [
    'linux',
    'docker',
    'elastic',
    'vnc',
    'prometheus',
    'opensearch',
]


# ═══════════════════════════════════════════════════════════════════════════════

class Plugin__Registry(Type_Safe):
    plugin_folders    : list                                    # set from PLUGIN_FOLDERS before discover(); tests can override
    manifests         : dict[str, Plugin__Manifest__Base]       # name → loaded manifest (enabled only)
    service_instances : dict                                    # name → live service instance (heterogeneous types)

    def discover(self) -> 'Plugin__Registry':
        for plugin_name in self.plugin_folders:
            if self.is_disabled_via_env(plugin_name):
                event_bus.emit('core:plugin.skipped', Schema__Plugin__Event(
                    name   = plugin_name,
                    reason = 'env-override-disabled',
                ))
                continue
            try:
                module       = import_module(f'sgraph_ai_service_playwright__cli.{plugin_name}.plugin')
                manifest_cls = self.find_manifest_class(module)                # finds Plugin__Manifest__* re-exported by plugin/__init__.py
                manifest     = manifest_cls()
                if not manifest.enabled:
                    event_bus.emit('core:plugin.skipped', Schema__Plugin__Event(
                        name   = plugin_name,
                        reason = 'manifest-disabled',
                    ))
                    continue
                self.manifests[str(manifest.name)] = manifest
                event_bus.emit('core:plugin.loaded', Schema__Plugin__Event(
                    name      = plugin_name,
                    stability = manifest.stability.value,
                ))
            except Exception as e:
                event_bus.emit('core:plugin.failed', Schema__Plugin__Event(
                    name  = plugin_name,
                    error = str(e),
                ))                                                              # continue — one broken plugin does not break startup
        return self

    def setup_all(self) -> 'Plugin__Registry':
        for name, manifest in self.manifests.items():
            manifest.setup()                                                    # manifest-level hook (e.g. download configs); usually no-op
            svc = manifest.service_class()()
            if hasattr(svc, 'setup'):                                           # services with lazy AWS-client init declare setup()
                svc.setup()
            self.service_instances[name] = svc
        return self

    def all_routes_classes(self) -> list:
        result = []
        for manifest in self.manifests.values():
            result.extend(manifest.routes_classes())
        return result

    def all_catalog_entries(self) -> list:
        return [m.catalog_entry() for m in self.manifests.values()]

    def service_for(self, plugin_name: str):
        return self.service_instances[plugin_name]

    @staticmethod
    def is_disabled_via_env(name: str) -> bool:                                # PLUGIN__{NAME}__ENABLED=false disables without redeploying
        env_key = f'PLUGIN__{name.upper()}__ENABLED'
        val     = os.environ.get(env_key, '').strip().lower()
        return val in ('false', '0', 'no', 'off')

    @staticmethod
    def find_manifest_class(module) -> type:                                    # finds the Plugin__Manifest__* class re-exported by plugin/__init__.py
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, Plugin__Manifest__Base)
                    and attr is not Plugin__Manifest__Base):
                return attr
        raise ImportError(f'{module.__name__}: no Plugin__Manifest__* subclass found')
