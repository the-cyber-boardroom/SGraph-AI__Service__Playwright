# ═══════════════════════════════════════════════════════════════════════════════
# tests — plugin manifests for all 8 types
# Verifies: registry discovers the 6 enabled manifests; catalog entries from
# manifests are identical to the existing hard-coded entries; prometheus and
# opensearch are skipped (disabled); neko and firefox are experimental+enabled.
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
from sgraph_ai_service_playwright__cli.firefox.plugin.Plugin__Manifest__Firefox      import Plugin__Manifest__Firefox
from sgraph_ai_service_playwright__cli.neko.plugin.Plugin__Manifest__Neko            import Plugin__Manifest__Neko
from sgraph_ai_service_playwright__cli.opensearch.plugin.Plugin__Manifest__OpenSearch import Plugin__Manifest__OpenSearch
from sgraph_ai_service_playwright__cli.podman.plugin.Plugin__Manifest__Podman        import Plugin__Manifest__Podman
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

    def test__discover__loads_exactly_6_enabled_plugins(self):
        registry = _make_registry()
        registry.discover()
        assert set(registry.manifests.keys()) == {'podman', 'docker', 'elastic', 'vnc', 'neko', 'firefox'}

    def test__discover__prometheus_and_opensearch_skipped(self):
        skipped_names = []
        event_bus.on('core:plugin.skipped', lambda p: skipped_names.append(str(p.name)))
        _make_registry().discover()
        assert 'prometheus'  in skipped_names
        assert 'opensearch'  in skipped_names

    def test__discover__6_loaded_events_fired(self):
        loaded = []
        event_bus.on('core:plugin.loaded', lambda p: loaded.append(str(p.name)))
        _make_registry().discover()
        assert set(loaded) == {'podman', 'docker', 'elastic', 'vnc', 'neko', 'firefox'}

    def test__plugin_folders__contains_all_8_types(self):
        assert set(PLUGIN_FOLDERS) == {'podman', 'docker', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox'}

    # ── individual manifest properties ───────────────────────────────────────

    def test__manifest_podman__properties(self):
        m = Plugin__Manifest__Podman()
        assert str(m.name)  == 'podman'
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

    def test__manifest_neko__enabled_experimental(self):
        m = Plugin__Manifest__Neko()
        assert str(m.name)  == 'neko'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.EXPERIMENTAL

    def test__manifest_firefox__enabled_experimental(self):
        m = Plugin__Manifest__Firefox()
        assert str(m.name)  == 'firefox'
        assert m.enabled    is True
        assert m.stability  == Enum__Plugin__Stability.EXPERIMENTAL

    # ── routes_classes ────────────────────────────────────────────────────────

    def test__manifest_podman__one_routes_class(self):
        from sgraph_ai_service_playwright__cli.podman.fast_api.routes.Routes__Podman__Stack import Routes__Podman__Stack
        assert Plugin__Manifest__Podman().routes_classes() == [Routes__Podman__Stack]

    def test__manifest_vnc__two_routes_classes(self):
        from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack import Routes__Vnc__Stack
        from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows import Routes__Vnc__Flows
        assert Plugin__Manifest__Vnc().routes_classes() == [Routes__Vnc__Stack, Routes__Vnc__Flows]

    # ── catalog entries: parity with existing hard-coded entries ─────────────

    def test__catalog_entries__match_existing_hardcoded(self):
        entries_obj = Stack__Catalog__Service__Entries()
        expected    = {
            'podman':  entries_obj.entry__podman(),
            'docker':  entries_obj.entry__docker(),
            'elastic': entries_obj.entry__elastic(),
            'vnc':     entries_obj.entry__vnc(),
        }
        manifests = {
            'podman':  Plugin__Manifest__Podman(),
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
        assert Plugin__Manifest__Podman()     .catalog_entry().type_id == Enum__Stack__Type.PODMAN
        assert Plugin__Manifest__Docker()     .catalog_entry().type_id == Enum__Stack__Type.DOCKER
        assert Plugin__Manifest__Elastic()    .catalog_entry().type_id == Enum__Stack__Type.ELASTIC
        assert Plugin__Manifest__Vnc()        .catalog_entry().type_id == Enum__Stack__Type.VNC
        assert Plugin__Manifest__Prometheus() .catalog_entry().type_id == Enum__Stack__Type.PROMETHEUS
        assert Plugin__Manifest__OpenSearch() .catalog_entry().type_id == Enum__Stack__Type.OPENSEARCH

    def test__catalog_entry__endpoint_paths_follow_convention(self):
        for manifest_cls, prefix in [
            (Plugin__Manifest__Podman,     'podman'),
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
            (Plugin__Manifest__Podman,  'podman'),
            (Plugin__Manifest__Docker,  'docker'),
            (Plugin__Manifest__Elastic, 'elastic'),
            (Plugin__Manifest__Vnc,     'vnc'),
        ]:
            topics = manifest_cls().event_topics_emitted()
            assert f'{prefix}:stack.created' in topics
            assert f'{prefix}:stack.deleted' in topics

    # ── service_class ─────────────────────────────────────────────────────────

    def test__service_class__each_manifest_returns_correct_type(self):
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Service      import Podman__Service
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Service      import Docker__Service
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service    import Elastic__Service
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service            import Vnc__Service

        assert Plugin__Manifest__Podman() .service_class() is Podman__Service
        assert Plugin__Manifest__Docker() .service_class() is Docker__Service
        assert Plugin__Manifest__Elastic().service_class() is Elastic__Service
        assert Plugin__Manifest__Vnc()    .service_class() is Vnc__Service

    # ── icon / boot_seconds_typical / nav_group / capabilities / soon ────────

    def test__manifest__icons_are_set(self):
        pairs = [
            (Plugin__Manifest__Docker(),     '🐳'),
            (Plugin__Manifest__Podman(),     '🦭'),
            (Plugin__Manifest__Elastic(),    '🔍'),
            (Plugin__Manifest__OpenSearch(), '🔎'),
            (Plugin__Manifest__Prometheus(), '📊'),
            (Plugin__Manifest__Vnc(),        '🖥️'),
            (Plugin__Manifest__Firefox(),    '🦊'),
            (Plugin__Manifest__Neko(),       '🦊'),
        ]
        for m, expected_icon in pairs:
            assert str(m.icon) == expected_icon, f'{m.name}: expected {expected_icon!r}, got {str(m.icon)!r}'

    def test__manifest__boot_seconds_typical(self):
        assert Plugin__Manifest__Docker()     .boot_seconds_typical == 600
        assert Plugin__Manifest__Podman()     .boot_seconds_typical == 120
        assert Plugin__Manifest__Elastic()    .boot_seconds_typical == 90
        assert Plugin__Manifest__OpenSearch() .boot_seconds_typical == 120
        assert Plugin__Manifest__Prometheus() .boot_seconds_typical == 90
        assert Plugin__Manifest__Vnc()        .boot_seconds_typical == 120
        assert Plugin__Manifest__Firefox()    .boot_seconds_typical == 90

    def test__manifest__nav_groups(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group import Enum__Plugin__Nav_Group
        assert Plugin__Manifest__Docker()     .nav_group == Enum__Plugin__Nav_Group.COMPUTE
        assert Plugin__Manifest__Podman()     .nav_group == Enum__Plugin__Nav_Group.COMPUTE
        assert Plugin__Manifest__Vnc()        .nav_group == Enum__Plugin__Nav_Group.COMPUTE
        assert Plugin__Manifest__Firefox()    .nav_group == Enum__Plugin__Nav_Group.COMPUTE
        assert Plugin__Manifest__Elastic()    .nav_group == Enum__Plugin__Nav_Group.OBSERVABILITY
        assert Plugin__Manifest__OpenSearch() .nav_group == Enum__Plugin__Nav_Group.OBSERVABILITY
        assert Plugin__Manifest__Prometheus() .nav_group == Enum__Plugin__Nav_Group.OBSERVABILITY

    def test__manifest__soon_flag(self):
        assert Plugin__Manifest__OpenSearch().soon is True
        assert Plugin__Manifest__Docker()    .soon is False
        assert Plugin__Manifest__Firefox()   .soon is False

    def test__manifest__capabilities_compute_plugins(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability import Enum__Plugin__Capability
        docker = Plugin__Manifest__Docker()
        assert Enum__Plugin__Capability.REMOTE_SHELL in list(docker.capabilities)
        assert Enum__Plugin__Capability.METRICS      in list(docker.capabilities)
        podman = Plugin__Manifest__Podman()
        assert Enum__Plugin__Capability.REMOTE_SHELL in list(podman.capabilities)

    def test__manifest__capabilities_observability_plugins(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability import Enum__Plugin__Capability
        elastic    = Plugin__Manifest__Elastic()
        prometheus = Plugin__Manifest__Prometheus()
        assert Enum__Plugin__Capability.METRICS in list(elastic.capabilities)
        assert Enum__Plugin__Capability.METRICS in list(prometheus.capabilities)

    def test__manifest__capabilities_vnc_and_firefox(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability import Enum__Plugin__Capability
        vnc     = Plugin__Manifest__Vnc()
        firefox = Plugin__Manifest__Firefox()
        assert Enum__Plugin__Capability.MITM_PROXY   in list(vnc.capabilities)
        assert Enum__Plugin__Capability.IFRAME_EMBED  in list(vnc.capabilities)
        assert Enum__Plugin__Capability.VAULT_WRITES  in list(firefox.capabilities)
        assert Enum__Plugin__Capability.AMI_BAKE      in list(firefox.capabilities)
        assert Enum__Plugin__Capability.MITM_PROXY    in list(firefox.capabilities)
        assert Enum__Plugin__Capability.IFRAME_EMBED  in list(firefox.capabilities)

    def test__manifest_entry__shape(self):
        from sgraph_ai_service_playwright__cli.core.plugin.schemas.Schema__Plugin__Manifest__Entry import Schema__Plugin__Manifest__Entry
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group           import Enum__Plugin__Nav_Group
        entry = Plugin__Manifest__Docker().manifest_entry()
        assert isinstance(entry, Schema__Plugin__Manifest__Entry)
        assert str(entry.icon)                 == '🐳'
        assert entry.boot_seconds_typical      == 600
        assert entry.nav_group                 == Enum__Plugin__Nav_Group.COMPUTE
        assert str(entry.create_endpoint_path) == '/docker/stack'
