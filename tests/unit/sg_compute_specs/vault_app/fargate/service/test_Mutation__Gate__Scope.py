# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Mutation__Gate__Scope
# Covers: inner gates set when outer gate is 1, NOT set when gate absent,
# original env values restored after exit (both normal + exception paths).
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Mutation__Gate__Scope import (
    Mutation__Gate__Scope,
    _GATE_ENV,
    _INNER_GATES,
)


class test_Mutation__Gate__Scope(TestCase):

    def setUp(self):
        # ensure no leftover gates from other tests
        os.environ.pop(_GATE_ENV, None)
        for k in _INNER_GATES:
            os.environ.pop(k, None)

    def tearDown(self):
        os.environ.pop(_GATE_ENV, None)
        for k in _INNER_GATES:
            os.environ.pop(k, None)

    # ── outer gate set ───────────────────────────────────────────────────────

    def test_inner_gates_set_when_outer_gate_is_1(self):
        os.environ[_GATE_ENV] = '1'
        with Mutation__Gate__Scope():
            for k in _INNER_GATES:
                assert os.environ.get(k) == '1', f'{k} not set to 1 inside scope'

    def test_inner_gates_restored_to_absent_after_exit(self):
        os.environ[_GATE_ENV] = '1'
        with Mutation__Gate__Scope():
            pass
        for k in _INNER_GATES:
            assert k not in os.environ, f'{k} still present after scope exit'

    def test_inner_gates_restore_previous_values_after_exit(self):
        os.environ[_GATE_ENV] = '1'
        os.environ['SG_AWS__FARGATE__ALLOW_MUTATIONS'] = 'prev'
        with Mutation__Gate__Scope():
            assert os.environ['SG_AWS__FARGATE__ALLOW_MUTATIONS'] == '1'
        assert os.environ['SG_AWS__FARGATE__ALLOW_MUTATIONS'] == 'prev'

    def test_inner_gates_restored_on_exception(self):
        os.environ[_GATE_ENV] = '1'
        try:
            with Mutation__Gate__Scope():
                raise RuntimeError('boom')
        except RuntimeError:
            pass
        for k in _INNER_GATES:
            assert k not in os.environ, f'{k} not restored after exception'

    # ── outer gate absent ────────────────────────────────────────────────────

    def test_inner_gates_not_set_when_outer_gate_absent(self):
        with Mutation__Gate__Scope():
            for k in _INNER_GATES:
                assert k not in os.environ, f'{k} set even though outer gate absent'

    def test_inner_gates_not_changed_when_outer_gate_absent(self):
        # pre-existing inner gate values must not be touched
        os.environ['SG_AWS__IAM__ALLOW_MUTATIONS'] = 'existing'
        with Mutation__Gate__Scope():
            assert os.environ.get('SG_AWS__IAM__ALLOW_MUTATIONS') == 'existing'
        assert os.environ.get('SG_AWS__IAM__ALLOW_MUTATIONS') == 'existing'

    def test_outer_gate_value_0_does_not_unlock_inner(self):
        os.environ[_GATE_ENV] = '0'
        with Mutation__Gate__Scope():
            for k in _INNER_GATES:
                assert k not in os.environ

    # ── context manager protocol ─────────────────────────────────────────────

    def test_scope_is_context_manager(self):
        scope = Mutation__Gate__Scope()
        assert hasattr(scope, '__enter__') and hasattr(scope, '__exit__')

    def test_scope_returns_self_on_enter(self):
        scope = Mutation__Gate__Scope()
        result = scope.__enter__()
        scope.__exit__(None, None, None)
        assert result is scope

    def test_all_four_inner_gates_are_covered(self):
        assert 'SG_AWS__FARGATE__ALLOW_MUTATIONS' in _INNER_GATES
        assert 'SG_AWS__IAM__ALLOW_MUTATIONS'     in _INNER_GATES
        assert 'SG_AWS__ECR__ALLOW_MUTATIONS'     in _INNER_GATES
        assert 'SG_AWS__LOGS__ALLOW_MUTATIONS'    in _INNER_GATES
        assert len(_INNER_GATES) == 4
