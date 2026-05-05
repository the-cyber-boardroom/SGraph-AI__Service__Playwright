# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__CLI__Loader
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.cli.Spec__CLI__Loader                                               import Spec__CLI__Loader, _spec_id_to_pascal


class test_Spec__CLI__Loader(TestCase):

    def setUp(self):
        self.loader = Spec__CLI__Loader()

    def test_spec_id_to_pascal_simple(self):
        assert _spec_id_to_pascal('docker')      == 'Docker'
        assert _spec_id_to_pascal('ollama')      == 'Ollama'
        assert _spec_id_to_pascal('open_design') == 'OpenDesign'

    def test_load_docker_returns_typer_app(self):
        import typer
        app = self.loader.load('docker')
        assert app is not None
        assert isinstance(app, typer.Typer)

    def test_load_unknown_spec_returns_none(self):
        assert self.loader.load('no_such_spec_xyz') is None

    def test_load_all_includes_docker(self):
        apps = self.loader.load_all(['docker', 'ollama', 'open_design'])
        assert 'docker' in apps

    def test_load_all_skips_specs_without_cli(self):
        apps = self.loader.load_all(['docker', 'no_such_spec_xyz'])
        assert 'no_such_spec_xyz' not in apps
        assert 'docker' in apps

    def test_load_all_empty_list(self):
        assert self.loader.load_all([]) == {}
