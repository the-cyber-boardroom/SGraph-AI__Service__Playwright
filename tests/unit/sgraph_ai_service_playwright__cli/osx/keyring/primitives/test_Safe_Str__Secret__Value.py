# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Secret__Value
#
# Companion to test_Safe_Str__AWS__Secret__Key.py — pins the alphabet for the
# generic-secret container so a future change can't silently regress to the
# Safe_Str default that strips /, +, = (the SignatureDoesNotMatch bug shape).
#
# This primitive is intentionally permissive: it accepts any printable ASCII
# plus common whitespace (\n \r \t). PEM keys, JWT tokens, base64 blobs, JSON
# config — all real-world secret shapes must survive the round-trip.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.osx.keyring.primitives.Safe_Str__Secret__Value import Safe_Str__Secret__Value


# Real-world secret shapes
_AWS_SECRET     = 'nv/jVHqu1234567890abcdefghijklmnopq+aaa='
_PEM_KEY        = '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEF\n-----END PRIVATE KEY-----'
_JWT_TOKEN      = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
_JSON_BLOB      = '{"key": "value", "list": [1, 2, 3], "nested": {"a": "b/c+d="}}'
_BASIC_AUTH     = 'dXNlcjpwYXNzdzByZCFAIyQ='     # base64 of "user:passw0rd!@#$"


class test_Safe_Str__Secret__Value(TestCase):

    def test__aws_secret_shape_round_trips(self):                          # SignatureDoesNotMatch reproducer (same shape as user-reported 2026-05-17)
        wrapped = Safe_Str__Secret__Value(_AWS_SECRET)
        assert str(wrapped) == _AWS_SECRET

    def test__pem_key_with_newlines_survives(self):                        # PEM keys are multi-line ASCII
        wrapped = Safe_Str__Secret__Value(_PEM_KEY)
        assert str(wrapped) == _PEM_KEY

    def test__jwt_token_with_dots_survives(self):                          # JWTs are three base64url chunks separated by dots
        wrapped = Safe_Str__Secret__Value(_JWT_TOKEN)
        assert str(wrapped) == _JWT_TOKEN

    def test__json_blob_survives(self):                                    # Stored config blobs commonly contain {} [] : , " and special chars
        wrapped = Safe_Str__Secret__Value(_JSON_BLOB)
        assert str(wrapped) == _JSON_BLOB

    def test__base64_padded_survives(self):                                # = padding chars
        wrapped = Safe_Str__Secret__Value(_BASIC_AUTH)
        assert str(wrapped) == _BASIC_AUTH

    def test__repr_is_masked(self):                                        # repr never leaks
        wrapped = Safe_Str__Secret__Value(_AWS_SECRET)
        assert repr(wrapped) == '****'
        assert _AWS_SECRET not in repr(wrapped)

    def test__control_bytes_are_scrubbed(self):                            # NUL / control bytes get replaced (likely indicates corruption)
        wrapped = Safe_Str__Secret__Value('normal\x00\x01\x02text')
        assert str(wrapped) == 'normal___text'

    def test__empty_is_allowed(self):                                      # allow_empty = True
        wrapped = Safe_Str__Secret__Value('')
        assert str(wrapped) == ''
