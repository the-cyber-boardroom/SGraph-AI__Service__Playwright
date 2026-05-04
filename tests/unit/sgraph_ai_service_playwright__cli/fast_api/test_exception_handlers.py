# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for fast_api.exception_handlers
# Covers the message-extraction parser directly so the response contract is
# locked down independently of the FastAPI plumbing (which is exercised
# end-to-end in test_Fast_API__SP__CLI.test_post_instances__rejects_invalid_deploy_name).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.fast_api.exception_handlers                  import extract_primitive_and_message


class test_extract_primitive_and_message(TestCase):

    def test__safe_str_regex_error(self):
        raw = 'in Safe_Str__Deploy_Name, value does not match required pattern: ^[a-z]{3,20}-[a-z]{3,20}$'
        primitive, message = extract_primitive_and_message(raw)
        assert primitive == 'Safe_Str__Deploy_Name'
        assert message   == 'value does not match required pattern: ^[a-z]{3,20}-[a-z]{3,20}$'

    def test__safe_str_empty_rejected(self):
        raw = 'in Safe_Str__Stack__Name, value cannot be None when allow_empty is False'
        primitive, message = extract_primitive_and_message(raw)
        assert primitive == 'Safe_Str__Stack__Name'
        assert 'allow_empty is False' in message

    def test__safe_int_boundary_error(self):
        raw = 'in Safe_UInt__Max_Hours, value 999 is above max_value 168'
        primitive, message = extract_primitive_and_message(raw)
        assert primitive == 'Safe_UInt__Max_Hours'
        assert 'above max_value 168' in message

    def test__non_primitive_message_passes_through(self):                           # Unknown shape → primitive='', message = original text (never a blank 500)
        raw = 'something completely unexpected happened'
        primitive, message = extract_primitive_and_message(raw)
        assert primitive == ''
        assert message   == raw

    def test__empty_or_none_safe(self):
        for raw in ('', None):
            primitive, message = extract_primitive_and_message(raw)
            assert primitive == ''
            assert message   == ''
