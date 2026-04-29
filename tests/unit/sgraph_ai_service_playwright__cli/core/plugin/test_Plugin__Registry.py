# ═══════════════════════════════════════════════════════════════════════════════
# tests — Plugin__Registry
# Uses sys.modules injection to simulate plugin module discovery without
# needing real plugin manifests on disk (those land in PR-2).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
from types    import ModuleType
from unittest import TestCase

from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                import event_bus
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base       import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry             import Plugin__Registry
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name \
                                                                                import Safe_Str__Plugin__Name


# ── fake manifests used across tests ─────────────────────────────────────────

class _Fake_Service:
    def setup(self): pass

class _Fake_Manifest__Enabled(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('fakeplugin')
    display_name : str                     = 'Fake Plugin'
    enabled      : bool                    = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):  return _Fake_Service
    def routes_classes(self): return []
    def catalog_entry(self):  return {'type_id': 'fake'}
    def setup(self):
        pass


class _Fake_Manifest__Disabled(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('disabledplugin')
    display_name : str                     = 'Disabled Plugin'
    enabled      : bool                    = False

    def service_class(self):  return _Fake_Service
    def routes_classes(self): return []
    def catalog_entry(self):  return {}


# ── helper: inject a fake module into sys.modules for a plugin name ──────────

def _inject_plugin_module(plugin_name: str, manifest_cls: type) -> str:
    module_path = f'sgraph_ai_service_playwright__cli.{plugin_name}.plugin'
    mod = ModuleType(module_path)
    setattr(mod, manifest_cls.__name__, manifest_cls)
    sys.modules[module_path] = mod
    return module_path


def _remove_plugin_module(plugin_name: str):
    module_path = f'sgraph_ai_service_playwright__cli.{plugin_name}.plugin'
    sys.modules.pop(module_path, None)


# ═══════════════════════════════════════════════════════════════════════════════

class test_Plugin__Registry(TestCase):

    def setUp(self):
        event_bus.reset()

    # ── discover: no plugins ─────────────────────────────────────────────────

    def test__discover__with_no_plugin_folders__loads_nothing(self):
        registry = Plugin__Registry()
        registry.discover()
        assert registry.manifests == {}

    # ── discover: enabled plugin ─────────────────────────────────────────────

    def test__discover__enabled_manifest__loaded__emits_loaded_event(self):
        _inject_plugin_module('fakeplugin', _Fake_Manifest__Enabled)
        loaded = []
        event_bus.on('core:plugin.loaded', lambda p: loaded.append(p))

        registry = Plugin__Registry()
        registry.plugin_folders = ['fakeplugin']
        registry.discover()

        assert 'fakeplugin' in registry.manifests
        assert len(loaded) == 1
        assert str(loaded[0].name) == 'fakeplugin'
        _remove_plugin_module('fakeplugin')

    # ── discover: manifest-disabled plugin ───────────────────────────────────

    def test__discover__manifest_disabled__skipped__emits_skipped_event(self):
        _inject_plugin_module('disabledplugin', _Fake_Manifest__Disabled)
        skipped = []
        event_bus.on('core:plugin.skipped', lambda p: skipped.append(p))

        registry = Plugin__Registry()
        registry.plugin_folders = ['disabledplugin']
        registry.discover()

        assert 'disabledplugin' not in registry.manifests
        assert len(skipped) == 1
        assert str(skipped[0].reason) == 'manifest-disabled'
        _remove_plugin_module('disabledplugin')

    # ── discover: env-var override disable ───────────────────────────────────

    def test__discover__env_override_disabled__skipped__module_not_imported(self):
        # env override fires BEFORE import — module need not exist
        os.environ['PLUGIN__ENVDISABLED__ENABLED'] = 'false'
        skipped = []
        event_bus.on('core:plugin.skipped', lambda p: skipped.append(p))

        registry = Plugin__Registry()
        registry.plugin_folders = ['envdisabled']
        registry.discover()

        assert 'envdisabled' not in registry.manifests
        assert len(skipped) == 1
        assert str(skipped[0].reason) == 'env-override-disabled'
        del os.environ['PLUGIN__ENVDISABLED__ENABLED']

    def test__is_disabled_via_env__various_falsy_values(self):
        for val in ('false', 'False', 'FALSE', '0', 'no', 'off'):
            os.environ['PLUGIN__X__ENABLED'] = val
            assert Plugin__Registry.is_disabled_via_env('x') is True
        del os.environ['PLUGIN__X__ENABLED']

    def test__is_disabled_via_env__absent_or_truthy__returns_false(self):
        os.environ.pop('PLUGIN__X__ENABLED', None)
        assert Plugin__Registry.is_disabled_via_env('x') is False
        os.environ['PLUGIN__X__ENABLED'] = 'true'
        assert Plugin__Registry.is_disabled_via_env('x') is False
        del os.environ['PLUGIN__X__ENABLED']

    # ── discover: broken import ───────────────────────────────────────────────

    def test__discover__broken_import__emits_failed_event__continues_with_rest(self):
        _inject_plugin_module('okplugin', _Fake_Manifest__Enabled)
        failed  = []
        loaded  = []
        event_bus.on('core:plugin.failed', lambda p: failed.append(p))
        event_bus.on('core:plugin.loaded', lambda p: loaded.append(p))

        registry = Plugin__Registry()
        registry.plugin_folders = ['nonexistent_broken_plugin', 'okplugin']
        registry.discover()

        assert len(failed) == 1
        assert 'nonexistent_broken_plugin' not in registry.manifests
        assert len(loaded) == 1                                                 # ok plugin still loaded despite earlier failure
        _remove_plugin_module('okplugin')

    # ── discover: multiple enabled plugins ────────────────────────────────────

    def test__discover__multiple_enabled__all_loaded(self):
        class _Manifest_A(_Fake_Manifest__Enabled):
            name : Safe_Str__Plugin__Name = Safe_Str__Plugin__Name('plugina')
        class _Manifest_B(_Fake_Manifest__Enabled):
            name : Safe_Str__Plugin__Name = Safe_Str__Plugin__Name('pluginb')

        _inject_plugin_module('plugina', _Manifest_A)
        _inject_plugin_module('pluginb', _Manifest_B)

        registry = Plugin__Registry()
        registry.plugin_folders = ['plugina', 'pluginb']
        registry.discover()

        assert 'plugina' in registry.manifests
        assert 'pluginb' in registry.manifests
        _remove_plugin_module('plugina')
        _remove_plugin_module('pluginb')

    # ── find_manifest_class ───────────────────────────────────────────────────

    def test__find_manifest_class__finds_subclass(self):
        mod = ModuleType('test_mod')
        setattr(mod, '_Fake_Manifest__Enabled', _Fake_Manifest__Enabled)
        cls = Plugin__Registry.find_manifest_class(mod)
        assert cls is _Fake_Manifest__Enabled

    def test__find_manifest_class__no_subclass__raises_import_error(self):
        mod = ModuleType('empty_mod')
        try:
            Plugin__Registry.find_manifest_class(mod)
            assert False, 'should have raised'
        except ImportError:
            pass

    # ── setup_all ─────────────────────────────────────────────────────────────

    def test__setup_all__instantiates_service_for_each_manifest(self):
        _inject_plugin_module('fakeplugin', _Fake_Manifest__Enabled)
        registry = Plugin__Registry()
        registry.plugin_folders = ['fakeplugin']
        registry.discover().setup_all()

        assert 'fakeplugin' in registry.service_instances
        assert isinstance(registry.service_instances['fakeplugin'], _Fake_Service)
        _remove_plugin_module('fakeplugin')

    # ── all_routes_classes / all_catalog_entries ──────────────────────────────

    def test__all_routes_classes__returns_combined_list(self):
        _inject_plugin_module('fakeplugin', _Fake_Manifest__Enabled)
        registry = Plugin__Registry()
        registry.plugin_folders = ['fakeplugin']
        registry.discover()
        assert registry.all_routes_classes() == []                             # _Fake_Manifest__Enabled returns []
        _remove_plugin_module('fakeplugin')

    def test__all_catalog_entries__returns_one_per_manifest(self):
        _inject_plugin_module('fakeplugin', _Fake_Manifest__Enabled)
        registry = Plugin__Registry()
        registry.plugin_folders = ['fakeplugin']
        registry.discover()
        entries = registry.all_catalog_entries()
        assert len(entries) == 1
        assert entries[0]   == {'type_id': 'fake'}
        _remove_plugin_module('fakeplugin')

    # ── service_for ───────────────────────────────────────────────────────────

    def test__service_for__returns_correct_instance(self):
        _inject_plugin_module('fakeplugin', _Fake_Manifest__Enabled)
        registry = Plugin__Registry()
        registry.plugin_folders = ['fakeplugin']
        registry.discover().setup_all()
        svc = registry.service_for('fakeplugin')
        assert isinstance(svc, _Fake_Service)
        _remove_plugin_module('fakeplugin')

    def test__service_for__unknown_plugin__raises_key_error(self):
        registry = Plugin__Registry()
        try:
            registry.service_for('nonexistent')
            assert False, 'should have raised'
        except KeyError:
            pass
