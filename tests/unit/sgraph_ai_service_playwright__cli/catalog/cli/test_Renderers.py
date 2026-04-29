# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for catalog Renderers
# ═══════════════════════════════════════════════════════════════════════════════

import io

from unittest                                                                       import TestCase

from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.catalog.cli.Renderers                        import render_stacks, render_types
from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Summary import List__Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Type__Catalog__Entry import List__Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary       import Schema__Stack__Summary
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary__List import Schema__Stack__Summary__List
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog import Schema__Stack__Type__Catalog
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry import Schema__Stack__Type__Catalog__Entry


def _capture(fn, *args):
    buf = io.StringIO()
    fn(*args, Console(file=buf, force_terminal=False, width=200))
    return buf.getvalue()


class test_render_types(TestCase):

    def test__empty(self):
        cat = Schema__Stack__Type__Catalog(entries=List__Schema__Stack__Type__Catalog__Entry())
        assert 'No stack types' in _capture(render_types, cat)

    def test__non_empty(self):
        entries = List__Schema__Stack__Type__Catalog__Entry()
        entries.append(Schema__Stack__Type__Catalog__Entry(type_id=Enum__Stack__Type.LINUX,
                                                              display_name='Bare Linux',
                                                              description='AL2023 + SSM',
                                                              available=True))
        out = _capture(render_types, Schema__Stack__Type__Catalog(entries=entries))
        assert 'linux'      in out
        assert 'Bare Linux' in out
        assert 'yes'        in out                                                  # available column


class test_render_stacks(TestCase):

    def test__empty(self):
        listing = Schema__Stack__Summary__List(stacks=List__Schema__Stack__Summary())
        assert 'No live stacks' in _capture(render_stacks, listing)

    def test__non_empty(self):
        stacks = List__Schema__Stack__Summary()
        stacks.append(Schema__Stack__Summary(type_id=Enum__Stack__Type.VNC,
                                              stack_name='vnc-prod',
                                              state='running', public_ip='5.6.7.8',
                                              region='eu-west-2',
                                              instance_id='i-0123456789abcdef0',
                                              uptime_seconds=3600))
        out = _capture(render_stacks, Schema__Stack__Summary__List(stacks=stacks))
        assert 'vnc'                  in out
        assert 'vnc-prod'             in out
        assert '5.6.7.8'              in out
