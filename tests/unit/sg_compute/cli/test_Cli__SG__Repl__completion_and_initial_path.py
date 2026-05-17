# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl tab completion + initial-path support
#
# Covers two REPL UX additions (2026-05-17):
#   - `sg repl aws bedrock` starts already navigated into aws/bedrock/
#   - readline tab completion walks the click tree from the REPL path
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import typer

from sg_compute.cli.Cli__SG__Repl import _completion_candidates


def _build_tree() -> typer.Typer:                                                # small synthetic click tree for deterministic tests
    root  = typer.Typer(name='sg', no_args_is_help=True)
    aws   = typer.Typer(name='aws')
    bed   = typer.Typer(name='bedrock')
    creds = typer.Typer(name='credentials')

    @bed.command('chat')
    def _chat(): pass

    @bed.command('check')
    def _check(): pass

    @bed.command('setup')
    def _setup(): pass

    @creds.command('list')
    def _list(): pass

    @creds.command('test')
    def _test(): pass

    aws.add_typer(bed,   name='bedrock')
    aws.add_typer(creds, name='credentials')
    root.add_typer(aws,  name='aws')

    @root.command('repl', hidden=True)
    def _repl(): pass

    return root


class test_completion_candidates(TestCase):

    def setUp(self):
        self.app = _build_tree()

    def test__empty_path_empty_prefix_lists_top_level(self):                     # at `sg/>` prompt, tab shows top-level groups
        candidates = _completion_candidates(self.app, [], [], '')
        assert 'aws' in candidates
        assert 'repl' not in candidates                                          # repl hidden at top level

    def test__empty_path_prefix_filters(self):
        candidates = _completion_candidates(self.app, [], [], 'aw')
        assert candidates == ['aws']

    def test__aws_path_lists_aws_children(self):
        candidates = _completion_candidates(self.app, ['aws'], [], '')
        assert 'bedrock'     in candidates
        assert 'credentials' in candidates

    def test__aws_bedrock_path_lists_verb_names(self):                           # inside aws/bedrock prompt
        candidates = _completion_candidates(self.app, ['aws', 'bedrock'], [], '')
        assert 'chat'  in candidates
        assert 'check' in candidates
        assert 'setup' in candidates

    def test__prefix_matches_at_inner_path(self):                                # `sg/aws/bedrock> che<TAB>` → check
        candidates = _completion_candidates(self.app, ['aws', 'bedrock'], [], 'che')
        assert candidates == ['check']

    def test__words_resolved_through_prior_segments(self):                       # `sg/aws> bedrock ch<TAB>` resolves bedrock first then completes ch*
        candidates = _completion_candidates(self.app, ['aws'], ['bedrock'], 'ch')
        assert 'chat'  in candidates
        assert 'check' in candidates

    def test__no_match_returns_empty(self):
        candidates = _completion_candidates(self.app, ['aws'], [], 'no-such-prefix')
        assert candidates == []
