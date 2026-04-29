# 01 — Plugin Registry & Manifest Design

**Status:** PROPOSED
**Read after:** `00__README__backend-plugin-architecture.md`
**Audience:** Sonnet implementing the backend track

---

## What this doc gives you

The shape of the plugin manifest, the registry that loads them, and the refactor of `Fast_API__SP__CLI` to use the registry. Concrete enough that you can build this without back-and-forth.

## Mental model

A **plugin** is a folder under `sgraph_ai_service_playwright__cli/{name}/` (already exists for current types) plus a small new sub-package: `{name}/plugin/`. The new sub-package contains:

- `Plugin__Manifest__{Name}.py` — single Type_Safe class declaring routes, service, catalog entry, enabled flag, event topics.
- `__init__.py` — exports the manifest class.

A **registry** is a single class (`Plugin__Registry`) that:

1. Knows the list of plugin folder names (hard-coded list — *not* filesystem scan; explicit beats implicit).
2. For each plugin, imports its manifest module *only if* the env-var override doesn't disable it.
3. Holds the loaded manifests in memory.
4. Exposes them to `Fast_API__SP__CLI.setup_routes()` and to `Stack__Catalog__Service`.

The registry is *the only thing* that imports plugin modules. Everything else asks the registry.

## Plugin manifest schema

```python
# sgraph_ai_service_playwright__cli/core/plugin/Plugin__Manifest__Base.py

from typing                                  import Type
from osbot_utils.type_safe.Type_Safe         import Type_Safe
from osbot_fast_api.api.routes.Fast_API_Routes import Fast_API_Routes

from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
    import Schema__Stack__Type__Catalog__Entry


class Plugin__Manifest__Base(Type_Safe):
    name             : str                                       # plugin id, lowercase, matches folder name (e.g. 'linux', 'vnc', 'neko')
    display_name     : str                                       # user-facing label (e.g. 'Bare Linux')
    description      : str                                       # one-line summary
    enabled          : bool         = False                      # default off — plugins must opt in
    stability        : str          = 'experimental'             # 'stable' | 'experimental' | 'deprecated'
    requires_aws     : bool         = True                       # set False for Neko-style local stubs

    # Lazy-instantiated on first access (so disabled plugins never run their setup)
    _service_instance              = None

    def service_class(self)        -> Type:                      # subclass-overridable
        raise NotImplementedError(f'{self.name}: service_class()')

    def routes_classes(self)       -> list[Type[Fast_API_Routes]]:
        raise NotImplementedError(f'{self.name}: routes_classes()')

    def catalog_entry(self)        -> Schema__Stack__Type__Catalog__Entry:
        """Build the catalog entry that the UI reads from /catalog/types.
           Implementations return a fully-populated entry — endpoint paths
           must match the routes_classes() prefixes."""
        raise NotImplementedError(f'{self.name}: catalog_entry()')

    def event_topics_emitted(self) -> list[str]:                 # for documentation + tests
        return []

    def event_topics_listened(self) -> list[str]:
        return []

    def setup(self)                -> None:
        """Optional plugin-level startup hook. Default no-op.
           Use for: lazy AWS client init that the service class needs.
           Called once per process at FastAPI startup, after registry load."""
        pass
```

### Concrete manifest example — VNC

```python
# sgraph_ai_service_playwright__cli/vnc/plugin/Plugin__Manifest__Vnc.py

from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base    import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                              import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type        import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack import Routes__Vnc__Stack
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows import Routes__Vnc__Flows
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service               import Vnc__Service


class Plugin__Manifest__Vnc(Plugin__Manifest__Base):
    name         : str  = 'vnc'
    display_name : str  = 'VNC bastion (browser-in-browser)'
    description  : str  = 'Full desktop browser-in-browser with mitmweb traffic inspection.'
    enabled      : bool = True
    stability    : str  = 'stable'

    def service_class(self):
        return Vnc__Service

    def routes_classes(self):
        return [Routes__Vnc__Stack, Routes__Vnc__Flows]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.VNC,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.large',
            default_max_hours     = 1,
            expected_boot_seconds = 90,
            create_endpoint_path  = '/vnc/stack',
            list_endpoint_path    = '/vnc/stacks',
            info_endpoint_path    = '/vnc/stack/{name}',
            delete_endpoint_path  = '/vnc/stack/{name}',
            health_endpoint_path  = '/vnc/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['vnc:stack.created', 'vnc:stack.deleted', 'vnc:stack.health.changed']

    def setup(self):
        if self._service_instance is None:
            self._service_instance = Vnc__Service()
            self._service_instance.setup()
```

The other 5 existing plugins (`linux`, `docker`, `elastic`, `prometheus`, `opensearch`) get the parallel manifest — straight migration of what's already in `Fast_API__SP__CLI.setup_routes()` today, just expressed declaratively in their own folder.

### Concrete manifest example — Neko (stub)

```python
# sgraph_ai_service_playwright__cli/neko/plugin/Plugin__Manifest__Neko.py

class Plugin__Manifest__Neko(Plugin__Manifest__Base):
    name         : str  = 'neko'
    display_name : str  = 'Neko (WebRTC browser)'
    description  : str  = 'Self-hosted browser via WebRTC streaming. Experimental.'
    enabled      : bool = False                                  # default off until evaluation completes
    stability    : str  = 'experimental'

    def service_class(self):
        from sgraph_ai_service_playwright__cli.neko.service.Neko__Service import Neko__Service
        return Neko__Service                                     # stub raises NotImplementedError on every method

    def routes_classes(self):
        from sgraph_ai_service_playwright__cli.neko.fast_api.routes.Routes__Neko__Stack import Routes__Neko__Stack
        return [Routes__Neko__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.NEKO,      # add to enum in this brief
            display_name          = self.display_name,
            description           = self.description,
            available             = False,                       # SOON tile
            default_instance_type = 't3.large',
            default_max_hours     = 1,
            expected_boot_seconds = 60,
            create_endpoint_path  = '/neko/stack',
            list_endpoint_path    = '/neko/stacks',
            info_endpoint_path    = '/neko/stack/{name}',
            delete_endpoint_path  = '/neko/stack/{name}',
            health_endpoint_path  = '/neko/stack/{name}/health',
        )
```

## The registry

```python
# sgraph_ai_service_playwright__cli/core/plugin/Plugin__Registry.py

import os
from importlib                                                                  import import_module

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base       import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                import event_bus    # see doc 02


# Hard-coded list — explicit beats filesystem scan. Adding a plugin = adding a line here.
PLUGIN_FOLDERS: list[str] = [
    'linux',
    'docker',
    'elastic',
    'vnc',
    'prometheus',
    'opensearch',
    'neko',
]


class Plugin__Registry(Type_Safe):
    manifests : dict[str, Plugin__Manifest__Base]                              # name → manifest

    def discover(self) -> 'Plugin__Registry':
        """Import each plugin's manifest module, instantiate, honour env-var
           override for `enabled`. Skips plugins whose env override is false
           — those modules are NOT imported at all (so an in-progress plugin
           can ship without breaking startup)."""
        for plugin_name in PLUGIN_FOLDERS:
            if self._is_disabled_via_env(plugin_name):
                event_bus.emit('core:plugin.skipped', {'name': plugin_name, 'reason': 'env-override-disabled'})
                continue
            try:
                module       = import_module(f'sgraph_ai_service_playwright__cli.{plugin_name}.plugin')
                manifest_cls = self._find_manifest_class(module)
                manifest     = manifest_cls()
                if not manifest.enabled:
                    event_bus.emit('core:plugin.skipped', {'name': plugin_name, 'reason': 'manifest-disabled'})
                    continue
                self.manifests[manifest.name] = manifest
                event_bus.emit('core:plugin.loaded', {'name': manifest.name, 'stability': manifest.stability})
            except Exception as e:
                event_bus.emit('core:plugin.failed', {'name': plugin_name, 'error': str(e)})
                # Continue with other plugins — one broken plugin does not break startup.
        return self

    def setup_all(self):
        """Call setup() on every loaded manifest (lazy aws_client init)."""
        for manifest in self.manifests.values():
            manifest.setup()

    def all_routes_classes(self) -> list:
        result = []
        for manifest in self.manifests.values():
            result.extend(manifest.routes_classes())
        return result

    def all_catalog_entries(self):
        return [m.catalog_entry() for m in self.manifests.values()]

    def service_for(self, plugin_name: str):
        """Returns the lazy-instantiated service for a plugin, or raises KeyError if not loaded."""
        manifest = self.manifests[plugin_name]
        return manifest._service_instance

    @staticmethod
    def _is_disabled_via_env(name: str) -> bool:
        """Honour env override: PLUGIN__{NAME}__ENABLED=false disables a plugin
           regardless of its manifest. Useful for ops to disable a misbehaving
           plugin without redeploying."""
        env_key = f'PLUGIN__{name.upper()}__ENABLED'
        val     = os.environ.get(env_key, '').strip().lower()
        return val in ('false', '0', 'no', 'off')

    @staticmethod
    def _find_manifest_class(module):
        """Find the Plugin__Manifest__{Name} class exported by the plugin's __init__.py."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                and issubclass(attr, Plugin__Manifest__Base)
                and attr is not Plugin__Manifest__Base):
                return attr
        raise ImportError(f'{module.__name__}: no Plugin__Manifest__* class found')
```

The `__init__.py` of each plugin's `plugin/` sub-package re-exports the manifest:

```python
# sgraph_ai_service_playwright__cli/vnc/plugin/__init__.py
from sgraph_ai_service_playwright__cli.vnc.plugin.Plugin__Manifest__Vnc import Plugin__Manifest__Vnc
```

## Refactoring `Fast_API__SP__CLI`

Today (89 lines, see `Fast_API__SP__CLI.py`):

```python
class Fast_API__SP__CLI(Serverless__Fast_API):
    catalog_service       : Stack__Catalog__Service
    docker_service        : Docker__Service
    ec2_service           : Ec2__Service
    elastic_service       : Elastic__Service
    linux_service         : Linux__Service
    observability_service : Observability__Service
    vnc_service           : Vnc__Service

    def setup(self):
        self.linux_service .setup()
        self.docker_service.setup()
        self.vnc_service   .setup()
        result = super().setup()
        register_type_safe_handlers(self.app())
        self.catalog_service.linux_service   = self.linux_service
        self.catalog_service.docker_service  = self.docker_service
        self.catalog_service.elastic_service = self.elastic_service
        self.catalog_service.vnc_service     = self.vnc_service
        self.setup_ui()
        return result

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog  , service=self.catalog_service      )
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Elastic__Stack  , service=self.elastic_service      )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        self.add_routes(Routes__Vnc__Stack      , service=self.vnc_service          )
        self.add_routes(Routes__Vnc__Flows      , service=self.vnc_service          )
```

After (target):

```python
class Fast_API__SP__CLI(Serverless__Fast_API):
    catalog_service       : Stack__Catalog__Service
    ec2_service           : Ec2__Service
    observability_service : Observability__Service
    plugin_registry       : Plugin__Registry                       # ← new

    def setup(self):
        self.plugin_registry.discover().setup_all()                # ← new: load all enabled plugins
        result = super().setup()
        register_type_safe_handlers(self.app())
        self.catalog_service.plugin_registry = self.plugin_registry  # catalog asks the registry, no per-service refs
        self.setup_ui()
        return result

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog , service=self.catalog_service     )
        self.add_routes(Routes__Ec2__Playwright, service=self.ec2_service         )
        self.add_routes(Routes__Observability  , service=self.observability_service)
        for routes_cls in self.plugin_registry.all_routes_classes():               # ← new: per-plugin routes
            manifest = self._manifest_owning(routes_cls)
            self.add_routes(routes_cls, service=manifest._service_instance)
```

Net change: ~30 lines → mounting becomes plugin-driven. Per-plugin imports gone.

## Refactoring `Stack__Catalog__Service`

Today: hard-coded `list_types()` returning a hand-built list; `list_all_stacks()` branching on type_id.

After:

```python
class Stack__Catalog__Service(Type_Safe):
    plugin_registry : Plugin__Registry

    def list_types(self) -> Schema__Stack__Type__Catalog__List:
        entries = self.plugin_registry.all_catalog_entries()
        return Schema__Stack__Type__Catalog__List(entries=entries)

    def list_all_stacks(self, region: str | None = None) -> Schema__Stack__List:
        result = []
        for manifest in self.plugin_registry.manifests.values():
            service = manifest._service_instance
            if hasattr(service, 'list_stacks'):                                   # protocol: plugins that implement list_stacks contribute
                result.extend(service.list_stacks(region=region))
        return Schema__Stack__List(stacks=result)
```

The "protocol-by-attribute" check (`hasattr(service, 'list_stacks')`) is deliberate and matches the existing duck-typed services. A future iteration can formalise via a `Plugin__Service__Base` interface; not in this brief.

## Folder layout summary (after this brief)

```
sgraph_ai_service_playwright__cli/
├── core/                                            ← NEW
│   ├── plugin/
│   │   ├── Plugin__Manifest__Base.py                ← NEW
│   │   ├── Plugin__Registry.py                      ← NEW
│   │   └── __init__.py
│   └── event_bus/
│       ├── Event__Bus.py                            ← NEW (see doc 02)
│       └── __init__.py
├── linux/
│   ├── ...existing folders unchanged...
│   └── plugin/                                      ← NEW
│       ├── Plugin__Manifest__Linux.py               ← NEW
│       └── __init__.py
├── docker/
│   ├── ...existing...
│   └── plugin/                                      ← NEW
├── elastic/
│   ├── ...existing...
│   └── plugin/                                      ← NEW
├── vnc/
│   ├── ...existing...
│   └── plugin/                                      ← NEW
├── prometheus/
│   ├── ...existing...
│   └── plugin/                                      ← NEW
├── opensearch/
│   ├── ...existing...
│   └── plugin/                                      ← NEW
├── neko/                                            ← NEW (entire folder)
│   ├── service/Neko__Service.py                     (stub — raises NotImplementedError)
│   ├── fast_api/routes/Routes__Neko__Stack.py       (stub — empty router)
│   ├── plugin/Plugin__Manifest__Neko.py             (enabled=False)
│   └── __init__.py
├── catalog/                                         ← MODIFIED (consumes registry)
├── ec2/                                             ← unchanged
├── fast_api/                                        ← MODIFIED (uses registry)
└── ...
```

## What good looks like

- One `grep` for `from sgraph_ai_service_playwright__cli.{plugin}` from another plugin's folder returns zero hits.
- `PLUGIN__VNC__ENABLED=false` env var → `/vnc/stack` returns 404, catalog entry for VNC is gone, no error in logs.
- A new compute type can be added by: (1) creating a new folder with the standard sub-structure, (2) adding the plugin name to `PLUGIN_FOLDERS`, (3) writing the manifest. **Zero changes to `Fast_API__SP__CLI` or `Stack__Catalog__Service`.**
- Tests for `Plugin__Registry` cover: all enabled, one disabled via manifest, one disabled via env, one with broken import (graceful degradation).
- `core:plugin.loaded`, `core:plugin.skipped`, `core:plugin.failed` events fire and are observable in tests.
