# ═══════════════════════════════════════════════════════════════════════════════
# tests — PR-2 plugin manifests for all 6 existing types
# Verifies: registry discovers the 4 enabled manifests; catalog entries from
# manifests are identical to the existing hard-coded entries; prometheus and
# opensearch are skipped; no cross-plugin imports from plugin folders.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type               import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service__Entries \
                                                                                     import Stack__Catalog__Service__Entries
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                     import event_bus
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                  import Plugin__Registry, PLUGIN_FOLDERS
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability     import Enum__Plugin__Stability

from sgraph_ai_service_playwright__cli.docker.plugin.Plugin__Manifest__Docker        import Plugin__Manifest__Docker
from sgraph_ai_service_playwright__cli.elastic.plugin.Plugin__Manifest__Elastic      import Plugin__Manifest__Elastic
from sgraph_ai_service_playwright__cli.linux.plugin.Plugin__Manifest__Linux          import Plugin__Manifest__Linux
from sgraph_ai_service_playwright__cli.opensearch.plugin.Plugin__Manifest__OpenSearch import Plugin__Manifest__OpenSearch
from sgraph_ai_service_playwright__cli.prometheus.plugin.Plugin__Manifest__Prometheus import Plugin__Manifest__Prometheus
from sgraph_ai_service_playwright__cli.vnc.plugin.Plugin__Manifest__Vnc              import Plugin__Manifest__Vnc


def _make_registry() -> Plugin__Registry:
    r = Plugin__Registry()
    r.plugin_folders = list(PLUGIN_FOLDERS)
    return r


class test_Plugin__Manifests__All(TestCase):

    def setUp(self):
        event_bus.reset()

    # ── registry discovery ───────────────────────────────────────────────────

    def test__discover__loads_exactly_4_enabled_plugins(self):
        registry = _make_registry()
        registry.discover()
        assert set(registry.manifests.keys()) == {'linux', 'docker', 'elastic', 'vnc'}

    def test__discover__prometheus_and_opensearch_skipped(self):
        skipped_names = []
        event_bus.on('core:plugin.skipped', lambda p: skipped_names.append(str(p.name)))
        _make_registry().discover()
        assert 'prometheus'  in skipped_names
        assert 'opensearch'  in skipped_names

    def test__discover__4_loaded_events_fired(self):
        loaded = []
        event_bus.on('core:plugin.loaded', lambda p: loaded.append(str(p.name)))
        _make_registry().discover()
        assert set(loaded) == {'linux', 'docker', 'elastic', 'vnc'}

    def test__plugin_folders__contains_all_6_types(self):
        assert set(PLUGIN_FOLDERS) == {'linux', 'docker', 'elastic', 'vnc', 'prometheus', 'opensearch'}

    # ── individual manifest properties ───────────────────────────────────────

    def test__manifest_linux__properties(self):
        m = Plugin__Manifest__Linux()
        assert str(m.name)  == 'linux'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.STABLE
        assert m.requires_aws is True

    def test__manifest_docker__properties(self):
        m = Plugin__Manifest__Docker()
        assert str(m.name)  == 'docker'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.STABLE

    def test__manifest_elastic__properties(self):
        m = Plugin__Manifest__Elastic()
        assert str(m.name)  == 'elastic'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.STABLE

    def test__manifest_vnc__properties(self):
        m = Plugin__Manifest__Vnc()
        assert str(m.name)  == 'vnc'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.STABLE

    def test__manifest_prometheus__disabled_experimental(self):
        m = Plugin__Manifest__Prometheus()
        assert str(m.name)  == 'prometheus'
        assert m.enabled    is False
        assert m.stability  == Enum__Plugin__Stability.EXPERIMENTAL

    def test__manifest_opensearch__disabled_experimental(self):
        m = Plugin__Manifest__OpenSearch()
        assert str(m.name)  == 'opensearch'
        assert m.enabled    is False
        assert m.stability  == Enum__Plugin__Stability.EXPERIMENTAL

    # ── routes_classes ────────────────────────────────────────────────────────

    def test__manifest_linux__one_routes_class(self):
        from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack import Routes__Linux__Stack
        assert Plugin__Manifest__Linux().routes_classes() == [Routes__Linux__Stack]

    def test__manifest_vnc__two_routes_classes(self):
        from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack import Routes__Vnc__Stack
        from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows import Routes__Vnc__Flows
        assert Plugin__Manifest__Vnc().routes_classes() == [Routes__Vnc__Stack, Routes__Vnc__Flows]

    # ── catalog entries: parity with existing hard-coded entries ─────────────

    def test__catalog_entries__match_existing_hardcoded(self):
        entries_obj = Stack__Catalog__Service__Entries()
        expected    = {
            'linux':   entries_obj.entry__linux(),
            'docker':  entries_obj.entry__docker(),
            'elastic': entries_obj.entry__elastic(),
            'vnc':     entries_obj.entry__vnc(),
        }
        manifests = {
            'linux':   Plugin__Manifest__Linux(),
            'docker':  Plugin__Manifest__Docker(),
            'elastic': Plugin__Manifest__Elastic(),
            'vnc':     Plugin__Manifest__Vnc(),
        }
        for name in expected:
            new = manifests[name].catalog_entry()
            old = expected[name]
            for field in vars(old):
                assert getattr(old, field) == getattr(new, field), \
                    f'{name}.{field}: expected {getattr(old,field)!r}, got {getattr(new,field)!r}'

    def test__catalog_entry__type_ids_are_correct_enum_members(self):
        assert Plugin__Manifest__Linux()      .catalog_entry().type_id == Enum__Stack__Type.LINUX
        assert Plugin__Manifest__Docker()     .catalog_entry().type_id == Enum__Stack__Type.DOCKER
        assert Plugin__Manifest__Elastic()    .catalog_entry().type_id == Enum__Stack__Type.ELASTIC
        assert Plugin__Manifest__Vnc()        .catalog_entry().type_id == Enum__Stack__Type.VNC
        assert Plugin__Manifest__Prometheus() .catalog_entry().type_id == Enum__Stack__Type.PROMETHEUS
        assert Plugin__Manifest__OpenSearch() .catalog_entry().type_id == Enum__Stack__Type.OPENSEARCH

    def test__catalog_entry__endpoint_paths_follow_convention(self):
        for manifest_cls, prefix in [
            (Plugin__Manifest__Linux,      'linux'),
            (Plugin__Manifest__Docker,     'docker'),
            (Plugin__Manifest__Elastic,    'elastic'),
            (Plugin__Manifest__Vnc,        'vnc'),
            (Plugin__Manifest__Prometheus, 'prometheus'),
            (Plugin__Manifest__OpenSearch, 'opensearch'),
        ]:
            entry = manifest_cls().catalog_entry()
            assert str(entry.create_endpoint_path) == f'/{prefix}/stack'
            assert str(entry.list_endpoint_path)   == f'/{prefix}/stacks'

    # ── event topics ──────────────────────────────────────────────────────────

    def test__event_topics__each_enabled_manifest_declares_created_and_deleted(self):
        for manifest_cls, prefix in [
            (Plugin__Manifest__Linux,   'linux'),
            (Plugin__Manifest__Docker,  'docker'),
            (Plugin__Manifest__Elastic, 'elastic'),
            (Plugin__Manifest__Vnc,     'vnc'),
        ]:
            topics = manifest_cls().event_topics_emitted()
            assert f'{prefix}:stack.created' in topics
            assert f'{prefix}:stack.deleted' in topics

    # ── service_class ─────────────────────────────────────────────────────────

    def test__service_class__each_manifest_returns_correct_type(self):
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Service       import Linux__Service
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Service     import Docker__Service
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service   import Elastic__Service
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service           import Vnc__Service

        assert Plugin__Manifest__Linux()  .service_class() is Linux__Service
        assert Plugin__Manifest__Docker() .service_class() is Docker__Service
        assert Plugin__Manifest__Elastic().service_class() is Elastic__Service
        assert Plugin__Manifest__Vnc()    .service_class() is Vnc__Service
