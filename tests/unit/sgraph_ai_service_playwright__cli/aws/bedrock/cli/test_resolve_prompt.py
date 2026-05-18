# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Verb__Bedrock__Chat__Helpers.resolve_prompt
#
# Regression coverage for two 2026-05-17 user-reported issues:
#
#   1. `nova "hello"`  — positional should work without --prompt (already fixed)
#   2. `nova what is your model?`  — unquoted multi-word should be collected
#      into a single prompt (REPL bug + chat-verb arity bug)
#
# The chat verbs accept a variadic positional (`Optional[List[str]]`); this
# helper handles joining and precedence (option > positional, error if empty).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import typer

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import resolve_prompt


class test_resolve_prompt(TestCase):

    def test__quoted_single_word_positional_list(self):                    # nova "hello" → ['hello']
        assert resolve_prompt(['hello'], None, None) == 'hello'

    def test__unquoted_multi_word_collected_into_list(self):               # nova what is your model? → ['what','is','your','model?']
        assert resolve_prompt(['what', 'is', 'your', 'model?'], None, None) == 'what is your model?'

    def test__quoted_phrase_as_single_list_item(self):                     # nova "what is your model?" → ['what is your model?']
        assert resolve_prompt(['what is your model?'], None, None) == 'what is your model?'

    def test__option_wins_over_positional(self):
        assert resolve_prompt(['ignored', 'words'], 'explicit prompt', None) == 'explicit prompt'

    def test__legacy_string_positional_still_works(self):                  # backwards-compat with older callers passing a plain str
        assert resolve_prompt('legacy single', None, None) == 'legacy single'

    def test__empty_list_and_no_option_and_no_input_raises(self):
        with self.assertRaises(typer.Exit):
            resolve_prompt([], None, None)

    def test__none_positional_and_no_option_and_no_input_raises(self):
        with self.assertRaises(typer.Exit):
            resolve_prompt(None, None, None)

    def test__empty_list_with_input_file_does_not_raise(self, tmpdir=None):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('content from file\n')
            path = f.name
        result = resolve_prompt([], None, path)
        assert 'content from file' in result
