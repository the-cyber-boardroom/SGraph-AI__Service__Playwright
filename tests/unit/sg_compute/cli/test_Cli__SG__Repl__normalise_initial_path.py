# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl.normalise_initial_path
#
# 2026-05-17 user request: `sg repl sg/aws/bedrock/tool/browser/session` should
# work (user copy-pasted the REPL prompt path back). Without this normaliser,
# Typer hands the path through as one big slash-separated string and the
# REPL's initial-path walker reports "not found".
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import normalise_initial_path


class test_normalise_initial_path(TestCase):

    # ── happy path ────────────────────────────────────────────────────────────

    def test__separate_words_unchanged(self):
        assert normalise_initial_path(['aws', 'bedrock']) == ['aws', 'bedrock']

    def test__single_string_with_slashes_is_split(self):                         # the user-reported case
        assert normalise_initial_path(['sg/aws/bedrock/tool/browser/session']) \
            == ['aws', 'bedrock', 'tool', 'browser', 'session']

    def test__leading_and_trailing_slashes_stripped(self):
        assert normalise_initial_path(['/aws/bedrock/']) == ['aws', 'bedrock']

    def test__mixed_slashes_and_words(self):
        assert normalise_initial_path(['aws/bedrock', 'chat']) == ['aws', 'bedrock', 'chat']

    # ── 'sg' prefix handling ─────────────────────────────────────────────────

    def test__bare_sg_prefix_returns_empty_path(self):
        assert normalise_initial_path(['sg']) == []

    def test__sg_prefix_inside_slash_string_stripped(self):
        assert normalise_initial_path(['sg/aws']) == ['aws']

    def test__sg_only_stripped_when_at_root(self):                               # `sg` inside the tree (e.g. as a verb name) should NOT be stripped
        assert normalise_initial_path(['aws', 'sg']) == ['aws', 'sg']

    # ── edge cases ────────────────────────────────────────────────────────────

    def test__none_returns_empty(self):
        assert normalise_initial_path(None) == []

    def test__empty_list_returns_empty(self):
        assert normalise_initial_path([]) == []

    def test__double_slashes_collapse(self):
        assert normalise_initial_path(['aws//bedrock']) == ['aws', 'bedrock']

    def test__whitespace_inside_segment_trimmed(self):
        assert normalise_initial_path([' aws ', ' bedrock ']) == ['aws', 'bedrock']

    def test__non_string_inputs_coerced(self):                                   # Typer passes strings; defensive against accidental int/None in the list
        assert normalise_initial_path(['aws', 'bedrock', '']) == ['aws', 'bedrock']
