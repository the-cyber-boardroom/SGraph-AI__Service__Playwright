# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for VNC Renderers
# Capture Console output via Console(file=...) and assert on rendered text.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import io

from unittest                                                                       import TestCase

from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.vnc.cli.Renderers                            import (render_create      ,
                                                                                              render_flows       ,
                                                                                              render_health      ,
                                                                                              render_info        ,
                                                                                              render_interceptors,
                                                                                              render_list        )
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary import List__Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary import Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Response import Schema__Vnc__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List         import Schema__Vnc__Stack__List


def _capture(fn, *args):
    buf = io.StringIO()
    fn(*args, Console(file=buf, force_terminal=False, width=200))
    return buf.getvalue()


def _info(state=Enum__Vnc__Stack__State.RUNNING, kind=Enum__Vnc__Interceptor__Kind.NONE, name=''):
    return Schema__Vnc__Stack__Info(stack_name='vnc-prod', instance_id='i-0123456789abcdef0',
                                      public_ip='5.6.7.8', viewer_url='https://5.6.7.8/',
                                      mitmweb_url='https://5.6.7.8/mitmweb/',
                                      region='eu-west-2', ami_id='ami-0685f8dd865c8e389',
                                      allowed_ip='1.2.3.4',
                                      interceptor_kind=kind, interceptor_name=name,
                                      state=state)


class test_render_list(TestCase):

    def test__empty(self):
        listing = Schema__Vnc__Stack__List(region='eu-west-2', stacks=List__Schema__Vnc__Stack__Info())
        assert 'No VNC stacks found' in _capture(render_list, listing)

    def test__non_empty(self):
        listing = Schema__Vnc__Stack__List(region='eu-west-2', stacks=List__Schema__Vnc__Stack__Info([_info()]))
        out     = _capture(render_list, listing)
        assert 'vnc-prod'            in out
        assert 'i-0123456789abcdef0' in out
        assert 'running'             in out


class test_render_info(TestCase):

    def test__includes_all_fields(self):
        out = _capture(render_info, _info(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger'))
        for needle in ('vnc-prod', 'eu-west-2', 'https://5.6.7.8/',
                       'https://5.6.7.8/mitmweb/', '1.2.3.4', 'header_logger'):
            assert needle in out, f'{needle!r} missing from info render'

    def test__interceptor_none_renders_label(self):
        out = _capture(render_info, _info())
        assert 'none' in out


class test_render_create(TestCase):

    def test__includes_password_warning_and_interceptor(self):
        resp = Schema__Vnc__Stack__Create__Response(stack_name='vnc-prod', instance_id='i-0123456789abcdef0',
                                                      region='eu-west-2', ami_id='ami-0685f8dd865c8e389',
                                                      viewer_url='https://5.6.7.8/',
                                                      mitmweb_url='https://5.6.7.8/mitmweb/',
                                                      operator_password='AAAA-BBBB-1234-cdef',
                                                      interceptor_kind=Enum__Vnc__Interceptor__Kind.NAME,
                                                      interceptor_name='header_logger',
                                                      state=Enum__Vnc__Stack__State.PENDING)
        out  = _capture(render_create, resp)
        assert 'AAAA-BBBB-1234-cdef' in out
        assert 'returned once'       in out
        assert 'self-signed TLS'     in out
        assert 'header_logger'       in out


class test_render_health(TestCase):

    def test__healthy(self):
        h   = Schema__Vnc__Health(stack_name='vnc-prod', state=Enum__Vnc__Stack__State.READY,
                                    nginx_ok=True, mitmweb_ok=True, flow_count=3)
        out = _capture(render_health, h)
        assert 'vnc-prod' in out
        assert 'ready'    in out
        assert 'yes'      in out
        assert '3'        in out

    def test__unhealthy_with_sentinel(self):
        h   = Schema__Vnc__Health(stack_name='vnc-prod', state=Enum__Vnc__Stack__State.UNKNOWN,
                                    nginx_ok=False, mitmweb_ok=False, flow_count=-1,
                                    error='instance not running')
        out = _capture(render_health, h)
        assert '—'                       in out
        assert 'instance not running'    in out


class test_render_flows(TestCase):

    def test__empty(self):
        out = _capture(render_flows, List__Schema__Vnc__Mitm__Flow__Summary())
        assert 'No mitmweb flows yet' in out

    def test__with_summaries(self):
        flows = List__Schema__Vnc__Mitm__Flow__Summary([
            Schema__Vnc__Mitm__Flow__Summary(flow_id='aaa', method='GET', url='https://example.com/x', status_code=200),
            Schema__Vnc__Mitm__Flow__Summary(flow_id='bbb', method='POST', url='https://example.com/y'),
        ])
        out = _capture(render_flows, flows)
        assert 'GET'                in out
        assert 'POST'               in out
        assert 'https://example.com/x' in out
        assert '200'                in out
        assert '—'                  in out                                          # status_code=0 renders as em-dash


class test_render_interceptors(TestCase):

    def test__empty(self):
        assert 'No baked example interceptors' in _capture(render_interceptors, [])

    def test__non_empty(self):
        out = _capture(render_interceptors, ['header_logger', 'flow_recorder'])
        assert 'header_logger' in out
        assert 'flow_recorder' in out
