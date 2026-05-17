# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl (Phase D)
# Tests REPL logic without running an actual interactive terminal.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl                                            import Cli__SG__Repl
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context  import Sg__Aws__Context


def _repl() -> Cli__SG__Repl:
    return Cli__SG__Repl(context=Sg__Aws__Context()).setup()


class test_Cli__SG__Repl__prompt(TestCase):

    def test__default_prompt_has_no_role(self):
        repl   = _repl()
        prompt = repl._prompt()
        assert prompt == 'sg> '

    def test__prompt_shows_role_when_set(self):
        repl = _repl()
        repl.context.set_role('admin')
        prompt = repl._prompt()
        assert prompt == 'sg [admin]> '

    def test__prompt_reverts_after_clear(self):
        repl = _repl()
        repl.context.set_role('admin')
        repl.context.clear_role()
        prompt = repl._prompt()
        assert prompt == 'sg> '


class test_Cli__SG__Repl__handle_as(TestCase):

    def test__as_role_sets_context(self):
        repl    = _repl()
        handled = repl._handle_as(['as', 'admin'])
        assert handled is True
        assert str(repl.context.current_role) == 'admin'

    def test__as_alone_clears_role(self):
        repl = _repl()
        repl.context.set_role('admin')
        handled = repl._handle_as(['as'])
        assert handled is True
        assert repl.context.has_role() is False

    def test__non_as_command_returns_false(self):
        repl    = _repl()
        handled = repl._handle_as(['credentials', 'list'])
        assert handled is False

    def test__empty_tokens_returns_false(self):
        repl    = _repl()
        handled = repl._handle_as([])
        assert handled is False

    def test__as_role_updates_prompt(self):
        repl = _repl()
        repl._handle_as(['as', 'dev'])
        assert '[dev]' in repl._prompt()


class test_Cli__SG__Repl__setup(TestCase):

    def test__setup_populates_exit_words(self):
        repl = _repl()
        assert 'exit' in repl.exit_words
        assert 'quit' in repl.exit_words
        assert 'q'    in repl.exit_words

    def test__setup_returns_self(self):
        repl   = Cli__SG__Repl(context=Sg__Aws__Context())
        result = repl.setup()
        assert result is repl
