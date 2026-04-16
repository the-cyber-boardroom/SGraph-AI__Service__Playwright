# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Identifier Primitives
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.primitives.identifiers import (
    Session_Id                                                           ,
    Sequence_Id                                                          ,
    Step_Id                                                              ,
    Safe_Str__Trace_Id                                                   ,
)


class test_Session_Id(TestCase):

    def test__auto_generates_value(self):                                           # Safe_Id generates a unique id when none supplied
        session_id = Session_Id()
        assert isinstance(session_id, Session_Id)
        assert str(session_id) != ''

    def test__accepts_explicit_value(self):
        session_id = Session_Id('session-abc-123')
        assert str(session_id) == 'session-abc-123'


class test_Sequence_Id(TestCase):

    def test__auto_generates_value(self):
        seq_id = Sequence_Id()
        assert isinstance(seq_id, Sequence_Id)
        assert str(seq_id) != ''

    def test__accepts_explicit_value(self):
        seq_id = Sequence_Id('seq-xyz-42')
        assert str(seq_id) == 'seq-xyz-42'


class test_Step_Id(TestCase):

    def test__accepts_alphanumerics_underscore_hyphen_dot(self):
        assert str(Step_Id('login-step.1'     )) == 'login-step.1'
        assert str(Step_Id('click_submit_btn' )) == 'click_submit_btn'
        assert str(Step_Id('step-01'          )) == 'step-01'

    def test__replaces_disallowed_chars(self):                                      # REPLACE mode substitutes disallowed chars with '_'
        assert str(Step_Id('bad step!'        )) == 'bad_step_'
        assert str(Step_Id('weird#chars@here' )) == 'weird_chars_here'

    def test__allows_empty(self):
        assert str(Step_Id('')) == ''


class test_Safe_Str__Trace_Id(TestCase):

    def test__accepts_hex_with_hyphens(self):
        assert str(Safe_Str__Trace_Id('abc-123-def')) == 'abc-123-def'
        assert str(Safe_Str__Trace_Id('deadbeef'   )) == 'deadbeef'

    def test__replaces_non_hex(self):                                               # Only lowercase hex a-f + digits + '-' survive; others → '_'
        assert str(Safe_Str__Trace_Id('ABC-XYZ-123')) == '___-___-123'

    def test__allows_empty(self):
        assert str(Safe_Str__Trace_Id('')) == ''

    def test__trims_whitespace(self):
        assert str(Safe_Str__Trace_Id('  abc123  ')) == 'abc123'
