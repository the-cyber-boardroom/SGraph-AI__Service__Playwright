# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl._apply_relative_navigation + full resolution pipeline
#
# 2026-05-17 user request: composite relative-nav forms inside the REPL.
#
#   sg/aws/bedrock/chat>  ../agent             # nav up one + run `agent`
#   sg/aws/bedrock/chat>  .. agent             # same, space-separated
#   sg/aws/bedrock/chat>  ../../aws/observe    # nav up two + run `aws observe`
#   sg/aws/bedrock/chat>  ..                   # nav up one (no-op verb)
#   sg/aws/bedrock/chat>  back                 # alias of ..
#
# Two layers of coverage:
#   (1) Unit tests on _apply_relative_navigation — pure helper, no Typer tree.
#   (2) Pipeline tests that walk
#         _extract_debug_flag → _maybe_absolute_dispatch
#         → _apply_relative_navigation → _resolve
#       against a synthetic Typer tree, to prove the new helper composes with
#       absolute-dispatch + debug-hoist + ambiguity handling — i.e. that
#       "everything else still works."
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import typer

from sg_compute.cli.Cli__SG__Repl import (_apply_relative_navigation,
                                          _extract_debug_flag        ,
                                          _maybe_absolute_dispatch   ,
                                          _resolve                   )


# ── Synthetic Typer tree used by the pipeline tests ──────────────────────────

def _build_tree() -> typer.Typer:                                                # mirrors the real sg-tree shape closely enough for resolution
    root    = typer.Typer(name='sg', no_args_is_help=True)
    aws     = typer.Typer(name='aws')
    bed     = typer.Typer(name='bedrock')
    chat    = typer.Typer(name='chat')
    agent   = typer.Typer(name='agent')
    observe = typer.Typer(name='observe')
    creds   = typer.Typer(name='credentials')

    @chat.command('nova')
    def _nova(): pass

    @chat.command('claude')
    def _claude(): pass

    @agent.command('run')
    def _agent_run(): pass

    @bed.command('check')
    def _bed_check(): pass

    @bed.command('setup')
    def _bed_setup(): pass

    @observe.command('tail')
    def _obs_tail(): pass

    @creds.command('list')
    def _creds_list(): pass

    bed.add_typer(chat,    name='chat')
    bed.add_typer(agent,   name='agent')
    aws.add_typer(bed,     name='bedrock')
    aws.add_typer(observe, name='observe')
    aws.add_typer(creds,   name='credentials')
    root.add_typer(aws,    name='aws')

    @root.command('repl', hidden=True)
    def _repl(): pass

    return root


# ═══════════════════════════════════════════════════════════════════════════════
# (1) Unit tests — _apply_relative_navigation
# ═══════════════════════════════════════════════════════════════════════════════

class test_apply_relative_navigation__core(TestCase):

    # ── single `..` / `back` / `.` ──────────────────────────────────────────

    def test__double_dot_pops_one_level(self):
        base, parts = _apply_relative_navigation(['..'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == []

    def test__back_alias_pops_one_level(self):
        base, parts = _apply_relative_navigation(['back'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == []

    def test__single_dot_is_noop(self):
        base, parts = _apply_relative_navigation(['.'], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == []

    def test__double_dot_at_root_is_silent_noop(self):                           # don't crash, don't go above root
        base, parts = _apply_relative_navigation(['..'], current_path=[])
        assert base  == []
        assert parts == []

    def test__back_at_root_is_silent_noop(self):
        base, parts = _apply_relative_navigation(['back'], current_path=[])
        assert base  == []
        assert parts == []

    # ── composite forms (the new edge cases) ────────────────────────────────

    def test__dotdot_slash_agent_pops_then_appends(self):                        # `../agent` from aws/bedrock/chat
        base, parts = _apply_relative_navigation(['../agent'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['agent']

    def test__dotdot_space_agent_pops_then_appends(self):                        # `.. agent` (two tokens, same result)
        base, parts = _apply_relative_navigation(['..', 'agent'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['agent']

    def test__dotdot_dotdot_aws_observe(self):                                   # `../../aws/observe` from aws/bedrock/chat
        base, parts = _apply_relative_navigation(['../../aws/observe'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws']
        assert parts == ['aws', 'observe']                                       # the literal 'aws' stays — _resolve will walk it

    def test__dotdot_dotdot_split_tokens(self):                                  # `../.. aws observe`
        base, parts = _apply_relative_navigation(['..', '..', 'aws', 'observe'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws']
        assert parts == ['aws', 'observe']

    def test__three_levels_up_partially_at_root(self):                           # `../../..` from one-deep → root, ignore extra ..
        base, parts = _apply_relative_navigation(['..', '..', '..'], current_path=['aws'])
        assert base  == []
        assert parts == []

    def test__dot_then_verb_runs_verb_under_current_path(self):                  # `./check` stays in place + appends 'check'
        base, parts = _apply_relative_navigation(['./check'], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['check']

    def test__leading_dot_token_then_verb(self):
        base, parts = _apply_relative_navigation(['.', 'check'], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['check']

    # ── navigation stops on first non-nav token ─────────────────────────────

    def test__dotdot_inside_a_verb_argument_is_not_navigation(self):             # `nova .. hello` — `..` inside an arg list is just a literal
        base, parts = _apply_relative_navigation(['nova', '..', 'hello'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock', 'chat']                               # current_path untouched (no leading ..)
        assert parts == ['nova', '..', 'hello']                                  # `..` preserved as a literal arg

    def test__verb_then_dotdot_then_more_keeps_dotdot_as_arg(self):
        base, parts = _apply_relative_navigation(['check', '..', 'foo'], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['check', '..', 'foo']

    # ── no-op / edge cases ──────────────────────────────────────────────────

    def test__no_parts_no_op(self):
        base, parts = _apply_relative_navigation([], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == []

    def test__verb_only_no_op(self):
        base, parts = _apply_relative_navigation(['check'], current_path=['aws', 'bedrock'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['check']

    def test__empty_current_path_with_verb(self):
        base, parts = _apply_relative_navigation(['aws'], current_path=[])
        assert base  == []
        assert parts == ['aws']

    def test__slash_in_token_after_pop_splits_into_multiple_parts(self):         # `../aws/bedrock` from aws/bedrock/chat → base=aws/bedrock, parts=[aws, bedrock]
        base, parts = _apply_relative_navigation(['../aws/bedrock'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['aws', 'bedrock']

    def test__current_path_is_not_mutated(self):                                 # helper must not modify caller's list
        original = ['aws', 'bedrock', 'chat']
        snapshot = list(original)
        _apply_relative_navigation(['..', 'agent'], current_path=original)
        assert original == snapshot

    def test__parts_input_is_not_mutated(self):
        parts_in = ['..', 'agent']
        snapshot = list(parts_in)
        _apply_relative_navigation(parts_in, current_path=['aws', 'bedrock', 'chat'])
        assert parts_in == snapshot

    def test__many_slashes_collapse_empty_segments(self):                        # `//../agent//` should ignore empty segs
        base, parts = _apply_relative_navigation(['//../agent//'], current_path=['aws', 'bedrock', 'chat'])
        assert base  == ['aws', 'bedrock']
        assert parts == ['agent']

    # ── post-navigation tokens are preserved as-is (regression 2026-05-17) ──
    # Bug: nav helper was splitting EVERY token on `/`, which mangled URLs
    # passed as arg values:
    #   `navigate <session-id> https://sgraph.ai`
    #     → ['navigate', '<session-id>', 'https:', 'sgraph.ai']
    #     → typer: "Got unexpected extra argument (sgraph.ai)"

    def test__url_arg_after_verb_is_not_split_on_slashes(self):
        base, parts = _apply_relative_navigation(
            ['navigate', 'abc-session', 'https://sgraph.ai'],
            current_path=['aws', 'bedrock', 'tool', 'browser', 'session'])
        assert base  == ['aws', 'bedrock', 'tool', 'browser', 'session']
        assert parts == ['navigate', 'abc-session', 'https://sgraph.ai']         # URL intact

    def test__s3_uri_arg_after_verb_is_not_split(self):
        base, parts = _apply_relative_navigation(
            ['upload', 's3://my-bucket/key/path.json'],
            current_path=['aws', 's3'])
        assert base  == ['aws', 's3']
        assert parts == ['upload', 's3://my-bucket/key/path.json']

    def test__file_path_arg_after_verb_is_not_split(self):
        base, parts = _apply_relative_navigation(
            ['put', '--file', 'path/to/file.json'],
            current_path=['aws', 's3'])
        assert base  == ['aws', 's3']
        assert parts == ['put', '--file', 'path/to/file.json']

    def test__nav_then_verb_then_url_combines_correctly(self):                   # `../navigate https://example.com`
        base, parts = _apply_relative_navigation(
            ['../navigate', 'abc-session', 'https://example.com'],
            current_path=['aws', 'bedrock', 'tool', 'browser', 'session', 'inner'])
        assert base  == ['aws', 'bedrock', 'tool', 'browser', 'session']
        assert parts == ['navigate', 'abc-session', 'https://example.com']


# ═══════════════════════════════════════════════════════════════════════════════
# (2) Pipeline tests — full REPL resolution chain
#     extract-debug → absolute-dispatch → relative-nav → _resolve
# ═══════════════════════════════════════════════════════════════════════════════

def _run_pipeline(app, current_path, line_tokens):
    """Mirror the REPL's exact ordering of helpers and return the final
    (resolved_path, trailing, debug_present) tuple a real run would compute.
    Returns (None, candidates, debug_present) when _resolve is ambiguous,
    or ('NAVIGATE_ONLY', new_path, debug_present) when navigation alone
    consumed the input (parts_clean empty after relative-nav)."""

    debug_present, parts_clean = _extract_debug_flag(line_tokens)
    dispatch_base, parts_clean = _maybe_absolute_dispatch(parts_clean, current_path)
    dispatch_base, parts_clean = _apply_relative_navigation(parts_clean, dispatch_base)

    if not parts_clean:
        return ('NAVIGATE_ONLY', dispatch_base, debug_present)

    resolved, trailing = _resolve(app, dispatch_base, parts_clean)
    if resolved is None:
        return (None, trailing, debug_present)
    return (resolved, trailing, debug_present)


class test_pipeline__new_edge_cases(TestCase):
    """The user-requested edge cases: `../agent`, `.. agent`, `../../aws/observe`."""

    def setUp(self):
        self.app = _build_tree()

    def test__dotdot_slash_agent_from_chat_navigates_to_agent_group(self):
        # `sg/aws/bedrock/chat>  ../agent`
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['../agent'])
        assert debug    is False
        assert resolved == ['aws', 'bedrock', 'agent']
        assert trailing == []

    def test__dotdot_space_agent_from_chat_navigates_to_agent_group(self):
        # `sg/aws/bedrock/chat>  .. agent`
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['..', 'agent'])
        assert debug    is False
        assert resolved == ['aws', 'bedrock', 'agent']
        assert trailing == []

    def test__three_dotdots_then_aws_observe_walks_from_root(self):
        # `sg/aws/bedrock/chat>  ../../../aws/observe` — three `..` to climb out
        # of the 3-deep path; remaining `aws/observe` walks from root.
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['../../../aws/observe'])
        assert debug    is False
        assert resolved == ['aws', 'observe']
        assert trailing == []

    def test__dotdot_dotdot_lands_at_aws__sibling_walk_misses_under_aws(self):
        # From `aws/bedrock/chat`, `../..` lands at `['aws']`. The remaining
        # `aws/observe` is then walked UNDER `aws` — there's no `aws` child of
        # `aws`, so resolution stops and the segments fall through as trailing
        # args. Documents the honest semantic: each `..` pops exactly one
        # level; to jump to a sibling subtree, type `aws/observe` directly
        # (absolute dispatch — see test_pipeline__regression below) or use
        # enough `..` to reach the root.
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['../../aws/observe'])
        assert resolved == ['aws']
        assert trailing == ['aws', 'observe']

    def test__bare_dotdot_is_navigation_only(self):                              # `..` alone — pure navigation
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['..'])
        assert debug    is False
        assert resolved == 'NAVIGATE_ONLY'                                       # sentinel from helper
        assert trailing == ['aws', 'bedrock']                                    # the new path

    def test__back_alone_is_navigation_only(self):
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock'],
                                                   line_tokens=['back'])
        assert resolved == 'NAVIGATE_ONLY'
        assert trailing == ['aws']

    def test__dotdot_then_run_verb_under_agent(self):                            # `.. agent run`
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['..', 'agent', 'run'])
        assert resolved == ['aws', 'bedrock', 'agent', 'run']
        assert trailing == []

    def test__dotdot_at_root_then_top_level_verb(self):                          # `.. aws bedrock check` from root
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=[],
                                                   line_tokens=['..', 'aws', 'bedrock', 'check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []


class test_pipeline__regression__everything_else_still_works(TestCase):
    """The other half of the user's brief: prove the new helper doesn't
    regress absolute dispatch, prefix resolution, debug-hoist, ambiguous
    matching, or option-flag handling."""

    def setUp(self):
        self.app = _build_tree()

    # ── absolute dispatch still works ──────────────────────────────────────

    def test__absolute_sg_path_from_deep_in_tree(self):                          # `sg aws bedrock check` from chat/
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['sg', 'aws', 'bedrock', 'check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__absolute_slash_first_token(self):
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'credentials'],
                                                   line_tokens=['/aws/bedrock', 'check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__absolute_with_slash_in_first_token(self):                          # `aws/bedrock check` from somewhere
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'credentials'],
                                                   line_tokens=['aws/bedrock', 'check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    # ── plain relative dispatch still works ────────────────────────────────

    def test__plain_verb_from_inside_a_group(self):                              # `check` at aws/bedrock
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock'],
                                                   line_tokens=['check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__multi_word_path_from_root(self):                                   # `aws bedrock check` from root
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=[],
                                                   line_tokens=['aws', 'bedrock', 'check'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__prefix_match_resolves_to_full_name(self):                          # `che` → `check`
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock'],
                                                   line_tokens=['che'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__ambiguous_prefix_returns_candidates(self):                         # `c` → matches 'check' AND 'chat' under bedrock
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock'],
                                                   line_tokens=['c'])
        assert resolved is None                                                  # ambiguous sentinel
        assert sorted(trailing) == ['chat', 'check']

    def test__verb_with_trailing_args_keeps_args(self):                          # `nova hello world` under chat/
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['nova', 'hello', 'world'])
        assert resolved == ['aws', 'bedrock', 'chat', 'nova']
        assert trailing == ['hello', 'world']

    def test__option_flag_stops_resolution(self):                                # `check --help` → resolved at check, --help in trailing
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock'],
                                                   line_tokens=['check', '--help'])
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == ['--help']

    # ── debug hoist still composes with the new helper ─────────────────────

    def test__debug_flag_with_relative_nav(self):                                # `../agent --debug run`
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['../agent', '--debug', 'run'])
        assert debug    is True                                                  # --debug stripped out + flag set
        assert resolved == ['aws', 'bedrock', 'agent', 'run']
        assert trailing == []

    def test__debug_flag_with_absolute_dispatch(self):                           # `sg aws bedrock -D check`
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock', 'chat'],
                                                  line_tokens=['sg', 'aws', 'bedrock', '-D', 'check'])
        assert debug    is True
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    def test__debug_flag_with_plain_verb(self):                                  # `check --debug` from aws/bedrock
        resolved, trailing, debug = _run_pipeline(self.app,
                                                  current_path=['aws', 'bedrock'],
                                                  line_tokens=['check', '--debug'])
        assert debug    is True
        assert resolved == ['aws', 'bedrock', 'check']
        assert trailing == []

    # ── interactions that must NOT trigger relative-nav ────────────────────

    def test__verb_argument_containing_dotdot_is_preserved(self):                # `nova .. foo` — `..` is the verb's arg, not navigation
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['nova', '..', 'foo'])
        assert resolved == ['aws', 'bedrock', 'chat', 'nova']                    # current path preserved
        assert trailing == ['..', 'foo']                                         # `..` passed through to the verb

    def test__plain_word_that_happens_to_be_back_is_treated_as_navigation(self):
        # Caveat documented in the helper: `back` is a navigation alias.
        # If a future verb is named `back`, this test will flag the collision.
        resolved, trailing, _debug = _run_pipeline(self.app,
                                                   current_path=['aws', 'bedrock', 'chat'],
                                                   line_tokens=['back'])
        assert resolved == 'NAVIGATE_ONLY'
        assert trailing == ['aws', 'bedrock']
