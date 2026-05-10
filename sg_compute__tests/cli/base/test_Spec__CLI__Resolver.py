# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__CLI__Resolver
# Verifies the auto-pick / prompt / error rule.  Uses Fake__ objects — no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
import typer
from unittest import TestCase

from sg_compute.cli.base.Spec__CLI__Resolver import Spec__CLI__Resolver


class _Stack:
    def __init__(self, name: str):
        self.stack_name = name


class _Listing:
    def __init__(self, names):
        self.stacks = [_Stack(n) for n in names]
        self.region = 'eu-west-2'


class _Svc:
    def __init__(self, names):
        self._names = names

    def list_stacks(self, region):
        return _Listing(self._names)


class test_Spec__CLI__Resolver(TestCase):

    def setUp(self):
        self.resolver = Spec__CLI__Resolver()

    def test_resolve__returns_provided_unchanged(self):
        svc    = _Svc([])
        result = self.resolver.resolve(svc, 'my-stack', 'eu-west-2', 'docker')
        assert result == 'my-stack'

    def test_resolve__zero_stacks_exits_1(self):
        svc = _Svc([])
        with pytest.raises(typer.Exit) as exc_info:
            self.resolver.resolve(svc, None, 'eu-west-2', 'ollama')
        assert exc_info.value.exit_code == 1

    def test_resolve__one_stack_auto_picked(self):
        svc    = _Svc(['fast-fermi'])
        result = self.resolver.resolve(svc, None, 'eu-west-2', 'docker')
        assert result == 'fast-fermi'

    def test_resolve__many_stacks_picks_valid_choice(self):
        svc = _Svc(['fast-fermi', 'quiet-hawk', 'bold-lynx'])

        original_prompt = typer.prompt

        def fake_prompt(msg, **kwargs):
            return 2

        typer.prompt = fake_prompt
        try:
            result = self.resolver.resolve(svc, None, 'eu-west-2', 'docker')
        finally:
            typer.prompt = original_prompt

        assert result == 'quiet-hawk'

    def test_resolve__many_stacks_invalid_input_exits_1(self):
        svc = _Svc(['fast-fermi', 'quiet-hawk'])

        def fake_prompt(msg, **kwargs):
            return 99

        original_prompt = typer.prompt
        typer.prompt    = fake_prompt
        try:
            with pytest.raises(typer.Exit) as exc_info:
                self.resolver.resolve(svc, None, 'eu-west-2', 'docker')
        finally:
            typer.prompt = original_prompt

        assert exc_info.value.exit_code == 1
