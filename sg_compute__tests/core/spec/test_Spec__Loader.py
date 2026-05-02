# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__Loader
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class test_Spec__Loader(TestCase):

    def setUp(self):
        self.loader = Spec__Loader()

    def test_load_all_returns_registry(self):
        registry = self.loader.load_all()
        assert isinstance(registry, Spec__Registry)

    def test_load_all_discovers_two_pilot_specs(self):
        registry = self.loader.load_all()
        assert len(registry) == 2
        assert 'ollama'      in registry.spec_ids()
        assert 'open_design' in registry.spec_ids()

    def test_manifests_are_typed(self):
        registry = self.loader.load_all()
        for entry in registry.all():
            assert isinstance(entry, Schema__Spec__Manifest__Entry)
            assert entry.spec_id     != ''
            assert entry.display_name != ''
            assert entry.version     != ''

    def test_catalogue_shape(self):
        registry  = self.loader.load_all()
        catalogue = registry.catalogue()
        assert len(catalogue.specs) == 2

    def test_get_spec_by_id(self):
        registry = self.loader.load_all()
        ollama   = registry.get('ollama')
        assert ollama is not None
        assert ollama.spec_id == 'ollama'
