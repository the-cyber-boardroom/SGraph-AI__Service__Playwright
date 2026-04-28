# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus Renderers
# Each renderer writes to a Console; tests capture the output via Console(file=...)
# and assert on the rendered substrings. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import io

from unittest                                                                       import TestCase

from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.prometheus.cli.Renderers                     import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Stack__Info import List__Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Response import Schema__Prom__Stack__Create__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__List import Schema__Prom__Stack__List


def _capture(fn, *args):                                                            # Rich Console writes to a StringIO; we get the rendered text
    buf = io.StringIO()
    fn(*args, Console(file=buf, force_terminal=False, width=200))
    return buf.getvalue()


def _info(state=Enum__Prom__Stack__State.RUNNING):
    return Schema__Prom__Stack__Info(stack_name='prom-prod', instance_id='i-0123456789abcdef0',
                                      public_ip='5.6.7.8', prometheus_url='http://5.6.7.8:9090/',
                                      region='eu-west-2', ami_id='ami-0685f8dd865c8e389',
                                      allowed_ip='1.2.3.4', state=state)


class test_render_list(TestCase):

    def test__empty(self):
        listing = Schema__Prom__Stack__List(region='eu-west-2', stacks=List__Schema__Prom__Stack__Info())
        out     = _capture(render_list, listing)
        assert 'No Prometheus stacks found' in out

    def test__non_empty_includes_stack_metadata(self):
        listing = Schema__Prom__Stack__List(region='eu-west-2',
                                              stacks=List__Schema__Prom__Stack__Info([_info()]))
        out     = _capture(render_list, listing)
        assert 'prom-prod'              in out
        assert 'i-0123456789abcdef0'    in out
        assert 'running'                in out
        assert '5.6.7.8'                in out


class test_render_info(TestCase):

    def test__includes_all_fields(self):
        out = _capture(render_info, _info())
        for needle in ('prom-prod', 'i-0123456789abcdef0', 'eu-west-2',
                       'ami-0685f8dd865c8e389', '5.6.7.8',
                       'http://5.6.7.8:9090/', '1.2.3.4'):
            assert needle in out, f'{needle} missing from info render'


class test_render_create(TestCase):

    def test__includes_url_and_target_count(self):
        resp = Schema__Prom__Stack__Create__Response(stack_name='prom-prod', instance_id='i-0123456789abcdef0',
                                                       region='eu-west-2', ami_id='ami-0685f8dd865c8e389',
                                                       prometheus_url='http://5.6.7.8:9090/',
                                                       targets_count=3,
                                                       state=Enum__Prom__Stack__State.PENDING)
        out  = _capture(render_create, resp)
        assert 'prom-prod'             in out
        assert 'http://5.6.7.8:9090/'  in out
        assert '3'                     in out                                        # targets-baked count
        assert 'password'      not in out.lower()                                    # P1: no password leaked


class test_render_health(TestCase):

    def test__healthy(self):
        h   = Schema__Prom__Health(stack_name='prom-prod', state=Enum__Prom__Stack__State.READY,
                                    prometheus_ok=True, targets_total=5, targets_up=4)
        out = _capture(render_health, h)
        assert 'prom-prod' in out
        assert 'ready'     in out
        assert 'yes'       in out                                                    # prometheus_ok rendered
        assert '5'         in out
        assert '4'         in out

    def test__unhealthy_with_sentinel_targets(self):
        h   = Schema__Prom__Health(stack_name='prom-prod', state=Enum__Prom__Stack__State.UNKNOWN,
                                    prometheus_ok=False, targets_total=-1, targets_up=-1,
                                    error='instance not running')
        out = _capture(render_health, h)
        assert '—'                       in out                                       # -1 sentinel renders as em-dash
        assert 'instance not running'    in out
        assert 'no'                      in out
