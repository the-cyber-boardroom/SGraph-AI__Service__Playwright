# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl bash-command escape
#
# 2026-05-17 user request: support common bash commands inside the REPL
# (cat, ls, pwd, etc.) without leaving the prompt, plus `!cmd` for arbitrary
# escape.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
import sys

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import _is_bash_command, _normalise_bang, BASH_WHITELIST


class test_is_bash_command(TestCase):

    def test__whitelist_member_is_bash(self):
        for cmd in ('cat', 'ls', 'pwd', 'grep', 'git', 'open', 'xdg-open'):
            assert _is_bash_command([cmd]), f'{cmd!r} should be whitelisted'

    def test__whitelist_member_with_args(self):
        assert _is_bash_command(['cat', '/etc/hosts'])
        assert _is_bash_command(['git', 'status'])

    def test__non_whitelist_is_not_bash(self):                                   # an sg subcommand must NOT be treated as bash
        assert not _is_bash_command(['nova', 'hello'])
        assert not _is_bash_command(['aws', 'bedrock'])

    def test__bang_prefix_is_always_bash(self):
        assert _is_bash_command(['!echo', 'foo'])
        assert _is_bash_command(['!', 'echo', 'foo'])
        assert _is_bash_command(['!python', '--version'])                        # python not in whitelist, but `!` allows anything

    def test__empty_parts_is_not_bash(self):
        assert not _is_bash_command([])

    def test__whitelist_is_explicit_not_a_catch_all(self):                       # safety: random unknown commands need explicit `!`
        assert not _is_bash_command(['rm', '-rf', '/'])                          # rm deliberately NOT in whitelist

    # ── sg-verb-wins-over-bash precedence (2026-05-17 user report) ──────────
    # At `sg/aws/s3>`, `ls` should run `sg aws s3 ls` (S3 listing), NOT bash
    # `ls`. Users can still force bash with explicit `!ls`.

    def test__sg_verb_wins_over_bash_whitelist(self):
        sg_children = {'ls', 'cat', 'cp', 'mv', 'rm'}                            # like `sg aws s3` exposes
        assert not _is_bash_command(['ls'],  sg_children=sg_children)            # `ls` → sg ls
        assert not _is_bash_command(['cat'], sg_children=sg_children)
        assert not _is_bash_command(['cp', 'a', 'b'], sg_children=sg_children)

    def test__bang_prefix_still_forces_bash_when_sg_verb_clashes(self):
        sg_children = {'ls'}
        assert _is_bash_command(['!ls'],  sg_children=sg_children)               # `!ls` → bash ls
        assert _is_bash_command(['!', 'ls'], sg_children=sg_children)

    def test__bash_whitelist_still_applies_when_no_sg_clash(self):
        sg_children = {'list', 'get'}                                            # `ls` not in children
        assert _is_bash_command(['ls'],   sg_children=sg_children)               # `ls` → bash (no clash)
        assert _is_bash_command(['pwd'],  sg_children=sg_children)

    def test__no_children_arg_preserves_legacy_behaviour(self):                  # backwards compat — call sites that don't supply children still work
        assert _is_bash_command(['ls'])                                          # no sg_children → bash whitelist alone


class test_normalise_bang(TestCase):

    def test__no_bang_passthrough(self):
        assert _normalise_bang(['cat', 'foo']) == ['cat', 'foo']

    def test__bang_attached(self):
        assert _normalise_bang(['!cat', 'foo']) == ['cat', 'foo']

    def test__bang_standalone(self):
        assert _normalise_bang(['!', 'cat', 'foo']) == ['cat', 'foo']

    def test__bang_only_returns_none(self):
        assert _normalise_bang(['!']) is None

    def test__empty_returns_empty(self):
        assert _normalise_bang([]) == []


class test_run_bash_end_to_end(TestCase):
    """Light integration — runs a real subprocess for `echo` and asserts the
    process completes. Doesn't capture stdout (it flows through to the test
    runner's terminal which is fine for pytest -s; otherwise just verifies
    no exception).
    """

    def test__echo_runs_without_error(self):
        from sg_compute.cli.Cli__SG__Repl import _run_bash
        # echo is universally available on Linux/Mac; if this test fails on
        # Windows the REPL bash escape isn't useful there either.
        _run_bash(['echo', 'hello from test'])                                   # would raise if subprocess failed in a way we don't catch

    def test__bang_echo_runs_without_error(self):
        from sg_compute.cli.Cli__SG__Repl import _run_bash
        _run_bash(['!echo', 'hello from test'])
