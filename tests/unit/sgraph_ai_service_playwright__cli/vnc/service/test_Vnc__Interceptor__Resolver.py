# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Interceptor__Resolver
# N5: three valid shapes; pure logic; no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Interceptor__Resolver       import (EXAMPLES,
                                                                                              NO_OP_SOURCE,
                                                                                              Vnc__Interceptor__Resolver,
                                                                                              list_examples)


class test_list_examples(TestCase):

    def test__examples_dict_is_non_empty_and_known(self):
        names = list_examples()
        assert 'header_logger'   in names
        assert 'header_injector' in names
        assert 'flow_recorder'   in names

    def test__every_example_imports_mitmproxy(self):                                # All baked examples should be valid mitmproxy addons
        for name, source in EXAMPLES.items():
            assert 'from mitmproxy' in source, f'{name!r} missing mitmproxy import'


class test_Vnc__Interceptor__Resolver(TestCase):

    def setUp(self):
        self.resolver = Vnc__Interceptor__Resolver()

    def test_resolve__defaults_to_no_op(self):                                      # N5 default-off
        source, label = self.resolver.resolve()
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_resolve__none_kind_explicit(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NONE)
        source, label = self.resolver.resolve(choice)
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_resolve__name_kind_returns_baked_example(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger')
        source, label = self.resolver.resolve(choice)
        assert source == EXAMPLES['header_logger']
        assert label  == 'header_logger'
        assert 'def request' in source                                              # Sanity: actually executable

    def test_resolve__name_kind_unknown_example_raises(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='not_real')
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve(choice)
        assert 'not_real'        in str(ctx.exception)
        assert 'header_logger'   in str(ctx.exception)                              # Listed in error to help operator

    def test_resolve__inline_kind_returns_operator_source_verbatim(self):
        src    = ('from mitmproxy import http\n\n'
                  'def request(flow: http.HTTPFlow) -> None:\n'
                  "    flow.request.headers['X-Test'] = 'inline'\n")
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE, inline_source=src)
        source, label = self.resolver.resolve(choice)
        assert source == src
        assert label  == 'inline'

    def test_resolve__inline_kind_empty_source_raises(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE)
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve(choice)
        assert 'non-empty' in str(ctx.exception)
