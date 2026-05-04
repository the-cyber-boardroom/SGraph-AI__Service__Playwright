# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__Routes__Loader
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.control_plane.Spec__Routes__Loader                           import Spec__Routes__Loader
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry


class test_Spec__Routes__Loader(TestCase):

    def setUp(self):
        self.registry = Spec__Loader().load_all()
        self.loader   = Spec__Routes__Loader(registry=self.registry)

    def test_load_returns_list_of_tuples(self):
        pairs = self.loader.load()
        assert isinstance(pairs, list)
        for spec_id, routes_cls in pairs:
            assert isinstance(spec_id,   str)
            assert isinstance(routes_cls, type)

    def test_load_discovers_docker_and_podman(self):
        pairs   = self.loader.load()
        spec_ids = [spec_id for spec_id, _ in pairs]
        assert 'docker' in spec_ids
        assert 'podman' in spec_ids

    def test_load_skips_specs_without_routes(self):
        # ollama has a manifest but no api/routes module → loader silently skips it
        pairs   = self.loader.load()
        spec_ids = [spec_id for spec_id, _ in pairs]
        assert 'ollama' not in spec_ids

    def test_routes_class_names_follow_convention(self):
        pairs = self.loader.load()
        for spec_id, routes_cls in pairs:
            pascal    = self.loader._to_pascal(spec_id)
            expected  = f'Routes__{pascal}__Stack'
            assert routes_cls.__name__ == expected, f'{spec_id}: expected {expected}'

    def test_to_pascal_simple(self):
        assert self.loader._to_pascal('docker')      == 'Docker'
        assert self.loader._to_pascal('open_design') == 'OpenDesign'
        assert self.loader._to_pascal('open-design') == 'Open-design'            # hyphens are not split

    def test_empty_registry_returns_empty_list(self):
        loader = Spec__Routes__Loader(registry=Spec__Registry())
        assert loader.load() == []

    def test_unknown_spec_id_returns_none(self):
        cls = self.loader._find_routes_class('nonexistent_spec')
        assert cls is None
