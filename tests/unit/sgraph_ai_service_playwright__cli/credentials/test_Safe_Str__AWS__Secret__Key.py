# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__AWS__Secret__Key
#
# Regression test for the SignatureDoesNotMatch bug: AWS secret keys use the
# base64 alphabet (A-Z, a-z, 0-9, /, +, =). Earlier versions inherited the
# Safe_Str default regex which silently replaced /, +, = with _, corrupting
# every secret on the load path through Credentials__Store.aws_credentials_get.
#
# These tests pin the regex so any future change must update both the
# implementation and the test together.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Secret__Key import Safe_Str__AWS__Secret__Key
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store            import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS              import Keyring__Mac__OS__In_Memory


# Realistic AWS-shaped secret keys: 40 chars, mixed case + digits + /+= base64 chars
_SECRET_WITH_SLASH_AND_PLUS = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY+'
_SECRET_USER_REPORTED       = 'nv/jVHqu1234567890abcdefghijklmnopq+aaa='   # shape that triggered the bug report 2026-05-17
_SECRET_ALPHANUMERIC_ONLY   = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJ1234'    # the only case that happened to work before the fix


class test_Safe_Str__AWS__Secret__Key__round_trip(TestCase):

    def test__slashes_and_pluses_survive(self):                                     # the SignatureDoesNotMatch reproducer
        wrapped = Safe_Str__AWS__Secret__Key(_SECRET_WITH_SLASH_AND_PLUS)
        assert str(wrapped) == _SECRET_WITH_SLASH_AND_PLUS

    def test__user_reported_shape_round_trips(self):                                # exact shape of the secret that triggered the bug
        wrapped = Safe_Str__AWS__Secret__Key(_SECRET_USER_REPORTED)
        assert str(wrapped) == _SECRET_USER_REPORTED

    def test__alphanumeric_only_still_works(self):                                  # the only case that worked pre-fix
        wrapped = Safe_Str__AWS__Secret__Key(_SECRET_ALPHANUMERIC_ONLY)
        assert str(wrapped) == _SECRET_ALPHANUMERIC_ONLY

    def test__equals_sign_padding_survives(self):                                   # base64 padding char
        wrapped = Safe_Str__AWS__Secret__Key('abc==')
        assert str(wrapped) == 'abc=='

    def test__repr_is_masked(self):                                                 # repr never leaks the secret
        wrapped = Safe_Str__AWS__Secret__Key(_SECRET_WITH_SLASH_AND_PLUS)
        assert repr(wrapped) == '****'
        assert _SECRET_WITH_SLASH_AND_PLUS not in repr(wrapped)

    def test__non_base64_char_replaced_with_underscore(self):                       # defines the allowed alphabet
        wrapped = Safe_Str__AWS__Secret__Key('hello world!')                        # space + ! are not in base64
        assert str(wrapped) == 'hello_world_'


class test_Credentials__Store__secret_round_trip(TestCase):                         # end-to-end: storage → load → unmangled secret

    def test__set_then_get__preserves_base64_secret(self):                          # the SignatureDoesNotMatch reproducer at the store level
        store = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        store.aws_credentials_set('dev', 'AKIAIOSFODNN7EXAMPLE', _SECRET_WITH_SLASH_AND_PLUS)
        creds = store.aws_credentials_get('dev')
        assert creds is not None
        assert str(creds.access_key) == 'AKIAIOSFODNN7EXAMPLE'
        assert str(creds.secret_key) == _SECRET_WITH_SLASH_AND_PLUS                 # before the fix this was mangled with underscores

    def test__user_reported_secret_shape_survives_store(self):
        store = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        store.aws_credentials_set('iam-admin', 'AKIA1234567890ABCDEF', _SECRET_USER_REPORTED)
        creds = store.aws_credentials_get('iam-admin')
        assert str(creds.secret_key) == _SECRET_USER_REPORTED
