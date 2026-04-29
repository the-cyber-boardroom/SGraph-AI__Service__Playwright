# ═══════════════════════════════════════════════════════════════════════════════
# tests — Neko plugin stub
# Verifies:
#   (a) manifest loads with enabled=False → registry skips it
#   (b) catalog entry present with available=False (SOON tile shape)
#   (c) service methods raise NotImplementedError when called directly
# No real AWS calls; no real Docker; plugin is intentionally unimplemented.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                 import Plugin__Registry
from sgraph_ai_service_playwright__cli.neko.plugin.Plugin__Manifest__Neko           import Plugin__Manifest__Neko
from sgraph_ai_service_playwright__cli.neko.service.Neko__Service                   import Neko__Service


class test_Neko__Plugin(TestCase):

    def setUp(self):
        event_bus.reset()

    # ── manifest ─────────────────────────────────────────────────────────────

    def test__manifest__enabled_false(self):
        manifest = Plugin__Manifest__Neko()
        assert manifest.enabled is False

    def test__manifest__stability_experimental(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability import Enum__Plugin__Stability
        manifest = Plugin__Manifest__Neko()
        assert manifest.stability == Enum__Plugin__Stability.EXPERIMENTAL

    def test__manifest__service_class_is_neko_service(self):
        assert Plugin__Manifest__Neko().service_class() is Neko__Service

    def test__manifest__routes_classes_nonempty(self):
        from sgraph_ai_service_playwright__cli.neko.fast_api.routes.Routes__Neko__Stack import Routes__Neko__Stack
        assert Routes__Neko__Stack in Plugin__Manifest__Neko().routes_classes()

    # ── catalog entry ─────────────────────────────────────────────────────────

    def test__catalog_entry__type_id_is_neko(self):
        entry = Plugin__Manifest__Neko().catalog_entry()
        assert entry.type_id == Enum__Stack__Type.NEKO

    def test__catalog_entry__available_false(self):
        entry = Plugin__Manifest__Neko().catalog_entry()
        assert entry.available is False                                          # shows as SOON tile in UI

    def test__catalog_entry__endpoints_reference_neko_prefix(self):
        entry = Plugin__Manifest__Neko().catalog_entry()
        assert '/neko/' in entry.create_endpoint_path
        assert '/neko/' in entry.list_endpoint_path

    # ── registry skips it ────────────────────────────────────────────────────

    def test__registry__skips_neko_manifest_disabled(self):
        skipped = []
        event_bus.on('core:plugin.skipped', lambda e: skipped.append(e))

        registry = Plugin__Registry()
        registry.plugin_folders = ['neko']
        registry.discover()

        assert 'neko' not in registry.manifests
        assert len(skipped) == 1
        assert skipped[0].name == 'neko'
        assert skipped[0].reason == 'manifest-disabled'

    # ── service stub raises ───────────────────────────────────────────────────

    def test__service__create_stack__raises_not_implemented(self):
        svc = Neko__Service()
        with self.assertRaises(NotImplementedError):
            svc.create_stack()

    def test__service__delete_stack__raises_not_implemented(self):
        svc = Neko__Service()
        with self.assertRaises(NotImplementedError):
            svc.delete_stack()

    def test__service__list_stacks__returns_empty(self):
        svc = Neko__Service()
        assert svc.list_stacks() == []
