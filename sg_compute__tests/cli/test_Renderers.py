# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — CLI Renderers
# ═══════════════════════════════════════════════════════════════════════════════

from io                                                                       import StringIO
from unittest                                                                 import TestCase

from rich.console                                                             import Console

from sg_compute.cli.Renderers                                                import (
    render_spec_catalogue,
    render_spec_entry,
    render_node_list,
    render_stack_list,
    render_pod_list,
)
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.pod.schemas.Schema__Pod__List                           import Schema__Pod__List
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.stack.schemas.Schema__Stack__List                       import Schema__Stack__List


def _console() -> tuple:
    buf = StringIO()
    c   = Console(file=buf, highlight=False, width=200)
    return c, buf


class test_Renderers(TestCase):

    def setUp(self):
        self.registry  = Spec__Loader().load_all()
        self.catalogue = self.registry.catalogue()

    def test_render_spec_catalogue_has_all_known_ids(self):
        c, buf = _console()
        render_spec_catalogue(self.catalogue, c)
        output = buf.getvalue()
        assert 'docker'      in output
        assert 'ollama'      in output
        assert 'open_design' in output
        assert 'podman'      in output

    def test_render_spec_catalogue_empty_message(self):
        from sg_compute.core.spec.schemas.Schema__Spec__Catalogue import Schema__Spec__Catalogue
        c, buf = _console()
        render_spec_catalogue(Schema__Spec__Catalogue(), c)
        assert 'No specs registered' in buf.getvalue()

    def test_render_spec_entry_docker(self):
        entry  = self.registry.get('docker')
        c, buf = _console()
        render_spec_entry(entry, c)
        output = buf.getvalue()
        assert 'docker'   in output
        assert 'Docker'   in output
        assert 'version'  in output
        assert 'stability' in output

    def test_render_node_list_empty(self):
        c, buf = _console()
        render_node_list(Schema__Node__List(), c)
        assert 'No nodes found' in buf.getvalue()

    def test_render_stack_list_empty(self):
        c, buf = _console()
        render_stack_list(Schema__Stack__List(), c)
        assert 'No stacks found' in buf.getvalue()

    def test_render_pod_list_empty(self):
        c, buf = _console()
        render_pod_list(Schema__Pod__List(), c)
        assert 'No pods found' in buf.getvalue()
