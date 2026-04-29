# ═══════════════════════════════════════════════════════════════════════════════
# tests — Plugin__Manifest__Base
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability     import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base            import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name


class _Concrete_Manifest(Plugin__Manifest__Base):                               # minimal concrete subclass for testing factory method dispatch
    name         : Safe_Str__Plugin__Name = Safe_Str__Plugin__Name('testplugin')
    display_name : str                    = 'Test Plugin'
    enabled      : bool                   = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):    return object
    def routes_classes(self):   return []
    def catalog_entry(self):    return {'type_id': 'test'}


class test_Plugin__Manifest__Base(TestCase):

    # ── defaults ─────────────────────────────────────────────────────────────

    def test__base_class__default_enabled_is_false(self):
        class _Min(Plugin__Manifest__Base):
            def service_class(self):  raise NotImplementedError
            def routes_classes(self): raise NotImplementedError
            def catalog_entry(self):  raise NotImplementedError
        m = _Min()
        assert m.enabled   is False
        assert m.stability == Enum__Plugin__Stability.EXPERIMENTAL
        assert m.requires_aws is True

    def test__base_class__abstract_methods_raise_not_implemented(self):
        m = Plugin__Manifest__Base()
        for method in ('service_class', 'routes_classes', 'catalog_entry'):
            try:
                getattr(m, method)()
                assert False, f'{method} should have raised'
            except NotImplementedError:
                pass

    def test__base_class__event_topics_return_empty_lists(self):
        m = Plugin__Manifest__Base()
        assert m.event_topics_emitted()  == []
        assert m.event_topics_listened() == []

    def test__base_class__setup_is_noop(self):
        m = Plugin__Manifest__Base()
        m.setup()                                                               # must not raise

    # ── concrete subclass ────────────────────────────────────────────────────

    def test__concrete__fields_set_correctly(self):
        m = _Concrete_Manifest()
        assert str(m.name)    == 'testplugin'
        assert m.enabled      is True
        assert m.stability    == Enum__Plugin__Stability.STABLE
        assert m.requires_aws is True

    def test__concrete__service_class__returns_type(self):
        m = _Concrete_Manifest()
        assert m.service_class() is object

    def test__concrete__routes_classes__returns_list(self):
        m = _Concrete_Manifest()
        assert m.routes_classes() == []

    def test__concrete__catalog_entry__returns_value(self):
        m = _Concrete_Manifest()
        assert m.catalog_entry() == {'type_id': 'test'}

    # ── Safe_Str__Plugin__Name validation ────────────────────────────────────

    def test__plugin_name__valid_lowercase_accepted(self):
        n = Safe_Str__Plugin__Name('linux')
        assert str(n) == 'linux'

    def test__plugin_name__uppercase_lowercased(self):
        n = Safe_Str__Plugin__Name('VNC')
        assert str(n) == 'vnc'

    def test__plugin_name__invalid_chars_rejected(self):
        try:
            Safe_Str__Plugin__Name('bad-name')
            assert False, 'should have raised'
        except Exception:
            pass

    # ── Enum__Plugin__Stability ───────────────────────────────────────────────

    def test__stability_enum__values(self):
        assert Enum__Plugin__Stability.STABLE.value       == 'stable'
        assert Enum__Plugin__Stability.EXPERIMENTAL.value == 'experimental'
        assert Enum__Plugin__Stability.DEPRECATED.value   == 'deprecated'
