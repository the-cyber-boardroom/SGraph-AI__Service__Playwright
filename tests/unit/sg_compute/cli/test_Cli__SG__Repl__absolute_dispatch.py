# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl._maybe_absolute_dispatch
#
# 2026-05-17 user request: error renderers print helpful next-step hints like
#   "Try: sg aws bedrock check"
# but those hints copy-pasted INTO the REPL fail with "No such command 'sg'"
# because the REPL dispatches relative to the current path.
#
# This helper recognises absolute forms (sg-prefix, leading slash, slash in
# first token) and re-bases dispatch to the root.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import _maybe_absolute_dispatch


class test_maybe_absolute_dispatch__absolute_forms(TestCase):

    def test__sg_prefix_re_bases_to_root(self):                                  # the user-reported case
        base, parts = _maybe_absolute_dispatch(
            ['sg', 'aws', 'bedrock', 'check'],
            current_path=['aws', 'bedrock', 'chat'])                             # user is deep in the tree
        assert base  == []
        assert parts == ['aws', 'bedrock', 'check']                              # rebased absolute path

    def test__leading_slash_first_token_is_absolute(self):
        base, parts = _maybe_absolute_dispatch(
            ['/aws/bedrock', 'check'],
            current_path=['some', 'where'])
        assert base  == []
        assert parts == ['aws', 'bedrock', 'check']

    def test__sg_slash_first_token_is_absolute(self):                            # `sg/aws/bedrock check` style
        base, parts = _maybe_absolute_dispatch(
            ['sg/aws/bedrock', 'check'],
            current_path=['somewhere'])
        assert base  == []
        assert parts == ['aws', 'bedrock', 'check']

    def test__slash_in_first_token_is_absolute(self):
        base, parts = _maybe_absolute_dispatch(
            ['aws/bedrock', 'check'],
            current_path=['some', 'where'])
        assert base  == []
        assert parts == ['aws', 'bedrock', 'check']


class test_maybe_absolute_dispatch__relative_forms(TestCase):

    def test__bare_word_stays_relative(self):
        base, parts = _maybe_absolute_dispatch(
            ['check'],
            current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']                                       # current_path preserved
        assert parts == ['check']

    def test__multiple_bare_words_stay_relative(self):
        base, parts = _maybe_absolute_dispatch(
            ['chat', 'nova', 'hello'],
            current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['chat', 'nova', 'hello']

    def test__option_flag_first_is_not_absolute(self):
        base, parts = _maybe_absolute_dispatch(
            ['--help'],
            current_path=['aws'])
        assert base  == ['aws']
        assert parts == ['--help']

    def test__empty_parts_no_op(self):
        base, parts = _maybe_absolute_dispatch([], current_path=['aws'])
        assert base  == ['aws']
        assert parts == []

    def test__short_option_flag_first_is_not_absolute(self):
        base, parts = _maybe_absolute_dispatch(['-p', 'value'], current_path=['aws'])
        assert base  == ['aws']
        assert parts == ['-p', 'value']
