# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Local__Docker__SGraph_AI__Service__Playwright
#
# Shape + pure-logic method checks (local_url, uvicorn_server_running,
# wait_for_uvicorn_server_running when container is None). Real container
# lifecycle lives in tests/docker/test_Local__Docker__SGraph-AI__Service__Playwright.py.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from sg_compute_specs.playwright.core.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base, LOCAL_PORT
from sg_compute_specs.playwright.core.docker.Local__Docker__SGraph_AI__Service__Playwright  import (LABEL_SOURCE                                 ,
                                                                                                 Local__Docker__SGraph_AI__Service__Playwright)


class test_class_shape(TestCase):

    def test__is_subclass_of_base(self):
        assert issubclass(Local__Docker__SGraph_AI__Service__Playwright,
                          Docker__SGraph_AI__Service__Playwright__Base)

    def test__defaults(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.label_source == LABEL_SOURCE
        assert local.local_port   == LOCAL_PORT
        assert local.container    is None

    def test__method_surface(self):
        for method in ('create_or_reuse_container', 'containers_with_label' ,
                       'delete_container'         , 'GET'                   ,
                       'POST'                     , 'local_url'             ,
                       'uvicorn_server_running'   , 'wait_for_uvicorn_server_running'):
            assert callable(getattr(Local__Docker__SGraph_AI__Service__Playwright, method)), \
                   f'missing method: {method}'


class test_local_url(TestCase):                                                         # Pure string logic; no daemon needed

    def test__prepends_slash_when_missing(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.local_url('health/info' ) == f'http://localhost:{LOCAL_PORT}/health/info'
        assert local.local_url('/health/info') == f'http://localhost:{LOCAL_PORT}/health/info'

    def test__empty_path_returns_root(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.local_url('') == f'http://localhost:{LOCAL_PORT}/'


class test_uvicorn_checks_without_container(TestCase):                                  # Defensive: methods work when container is None

    def test__uvicorn_server_running_returns_false_when_no_container(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.uvicorn_server_running() is False

    def test__wait_for_uvicorn_returns_false_immediately_when_no_container(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.wait_for_uvicorn_server_running() is False

    def test__delete_container_returns_false_when_no_container(self):
        local = Local__Docker__SGraph_AI__Service__Playwright()
        assert local.delete_container() is False
