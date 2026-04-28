# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Renderers
# Each renderer writes to a Console; tests capture the output via Console(file=...)
# and assert on the rendered substrings. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import io

from unittest                                                                       import TestCase

from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.opensearch.cli.Renderers                     import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.opensearch.collections.List__Schema__OS__Stack__Info import List__Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Health        import Schema__OS__Health
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Response import Schema__OS__Stack__Create__Response
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__List   import Schema__OS__Stack__List


def _capture(fn, *args):                                                            # Rich Console writes to a StringIO; we get the rendered text
    buf = io.StringIO()
    fn(*args, Console(file=buf, force_terminal=False, width=200))
    return buf.getvalue()


def _info(state=Enum__OS__Stack__State.RUNNING):
    return Schema__OS__Stack__Info(stack_name='os-prod', instance_id='i-0123456789abcdef0',
                                    public_ip='5.6.7.8', dashboards_url='https://5.6.7.8/',
                                    os_endpoint='https://5.6.7.8:9200/', region='eu-west-2',
                                    ami_id='ami-0685f8dd865c8e389', allowed_ip='1.2.3.4',
                                    state=state)


class test_render_list(TestCase):

    def test__empty(self):
        listing = Schema__OS__Stack__List(region='eu-west-2', stacks=List__Schema__OS__Stack__Info())
        out     = _capture(render_list, listing)
        assert 'No OpenSearch stacks found' in out

    def test__non_empty_includes_stack_metadata(self):
        listing = Schema__OS__Stack__List(region='eu-west-2',
                                            stacks=List__Schema__OS__Stack__Info([_info()]))
        out     = _capture(render_list, listing)
        assert 'os-prod'                in out
        assert 'i-0123456789abcdef0'    in out
        assert 'running'                in out
        assert '5.6.7.8'                in out


class test_render_info(TestCase):

    def test__includes_all_fields(self):
        out = _capture(render_info, _info())
        for needle in ('os-prod', 'i-0123456789abcdef0', 'eu-west-2',
                       'ami-0685f8dd865c8e389', '5.6.7.8',
                       'https://5.6.7.8/', 'https://5.6.7.8:9200/', '1.2.3.4'):
            assert needle in out, f'{needle} missing from info render'


class test_render_create(TestCase):

    def test__includes_password_warning(self):
        resp = Schema__OS__Stack__Create__Response(stack_name='os-prod', instance_id='i-0123456789abcdef0',
                                                     region='eu-west-2', ami_id='ami-0685f8dd865c8e389',
                                                     dashboards_url='https://5.6.7.8/',
                                                     admin_password='AAAA-BBBB-1234-cdef',
                                                     state=Enum__OS__Stack__State.PENDING)
        out  = _capture(render_create, resp)
        assert 'os-prod'                  in out
        assert 'AAAA-BBBB-1234-cdef'      in out                                    # The secret renders
        assert 'returned once'            in out                                    # And the warning is loud
        assert 'self-signed TLS'          in out                                    # Reminds about cert acceptance


class test_render_health(TestCase):

    def test__healthy(self):
        h   = Schema__OS__Health(stack_name='os-prod', state=Enum__OS__Stack__State.READY,
                                  cluster_status='green', node_count=1, active_shards=5,
                                  dashboards_ok=True, os_endpoint_ok=True)
        out = _capture(render_health, h)
        assert 'os-prod'      in out
        assert 'ready'        in out
        assert 'green'        in out
        assert 'yes'          in out                                                # dashboards_ok / os_endpoint_ok rendered as 'yes'

    def test__unhealthy_with_sentinel_node_count(self):
        h   = Schema__OS__Health(stack_name='os-prod', state=Enum__OS__Stack__State.UNKNOWN,
                                  node_count=-1, active_shards=-1,
                                  dashboards_ok=False, os_endpoint_ok=False,
                                  error='instance not running')
        out = _capture(render_health, h)
        assert '—'                          in out                                    # -1 sentinel renders as em-dash
        assert 'instance not running'       in out
        assert 'no'                          in out
