# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: tests for Vnc__Interceptor__Resolver
# Pure logic — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.schemas.Schema__Vnc__Interceptor__Choice                  import Schema__Vnc__Interceptor__Choice
from sg_compute_specs.vnc.service.Vnc__Interceptor__Resolver                        import (EXAMPLES                   ,
                                                                                             NO_OP_SOURCE               ,
                                                                                             Vnc__Interceptor__Resolver ,
                                                                                             list_examples              )


class test_Vnc__Interceptor__Resolver(TestCase):

    def setUp(self):
        self.resolver = Vnc__Interceptor__Resolver()

    def test_examples_dict_has_three_keys(self):
        assert len(EXAMPLES) == 3
        assert 'header_logger'   in EXAMPLES
        assert 'header_injector' in EXAMPLES
        assert 'flow_recorder'   in EXAMPLES

    def test_list_examples_is_sorted(self):
        names = list_examples()
        assert names == sorted(names)

    def test_resolve_none_returns_no_op_source(self):
        choice        = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NONE)
        source, label = self.resolver.resolve(choice)
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_resolve_default_choice_returns_no_op(self):
        source, label = self.resolver.resolve()
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_resolve_name_header_logger(self):
        choice        = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME,
                                                          name='header_logger')
        source, label = self.resolver.resolve(choice)
        assert 'header_logger' in source
        assert label == 'header_logger'

    def test_resolve_name_unknown_raises(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME,
                                                   name='nonexistent_example')
        with self.assertRaises(ValueError):
            self.resolver.resolve(choice)

    def test_resolve_inline_returns_source_and_inline_label(self):
        inline_py     = "# my custom interceptor\n"
        choice        = Schema__Vnc__Interceptor__Choice(kind          = Enum__Vnc__Interceptor__Kind.INLINE,
                                                          inline_source = inline_py)
        source, label = self.resolver.resolve(choice)
        assert source == inline_py
        assert label  == 'inline'

    def test_resolve_inline_empty_raises(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE)
        with self.assertRaises(ValueError):
            self.resolver.resolve(choice)
