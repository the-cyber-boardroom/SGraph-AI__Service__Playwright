# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Mutation__Gate
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pytest

import typer
import click

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate import require_mutation_gate


ENV_VAR = 'SG_AWS__TEST__ALLOW_MUTATIONS'


def _make_guarded():
    @require_mutation_gate(ENV_VAR)
    def _action():
        return 'executed'
    return _action


class Test__Mutation__Gate:

    def test_blocks_when_env_unset(self):
        os.environ.pop(ENV_VAR, None)
        fn = _make_guarded()
        with pytest.raises(click.exceptions.Exit):
            fn()

    def test_blocks_when_env_zero(self):
        os.environ[ENV_VAR] = '0'
        fn = _make_guarded()
        with pytest.raises(click.exceptions.Exit):
            fn()
        del os.environ[ENV_VAR]

    def test_passes_when_env_one(self):
        os.environ[ENV_VAR] = '1'
        fn = _make_guarded()
        result = fn()
        assert result == 'executed'
        del os.environ[ENV_VAR]

    def test_decorator_preserves_name(self):
        @require_mutation_gate(ENV_VAR)
        def my_command():
            pass
        assert my_command.__name__ == 'my_command'
