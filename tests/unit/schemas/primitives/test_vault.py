# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault Primitives
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.primitives.vault import (
    Safe_Str__Vault_Key                                                  ,
    Safe_Str__Vault_Path                                                 ,
)


class test_Safe_Str__Vault_Key(TestCase):

    def test__accepts_friendly_format(self):                                        # e.g. "drum-hunt-6610"
        assert str(Safe_Str__Vault_Key('drum-hunt-6610')) == 'drum-hunt-6610'

    def test__accepts_opaque_format(self):                                          # e.g. "j4pyy0lhny8jx7osqn4lclhq:mzrp0li8"
        key = 'b8cvhl2kk1tg0fw7cokp9xdh:ozgwi1rr'
        assert str(Safe_Str__Vault_Key(key)) == key

    def test__replaces_uppercase_chars(self):                                       # REPLACE substitutes uppercase chars with '_'
        assert str(Safe_Str__Vault_Key('AbC-123')) == '_b_-123'

    def test__replaces_spaces_and_punctuation(self):
        assert str(Safe_Str__Vault_Key('bad key!here')) == 'bad_key_here'

    def test__trims_whitespace(self):
        assert str(Safe_Str__Vault_Key('  valid-key  ')) == 'valid-key'


class test_Safe_Str__Vault_Path(TestCase):

    def test__accepts_slash_path(self):
        p = '/sessions/openrouter/cookies.json'
        assert str(Safe_Str__Vault_Path(p)) == p

    def test__accepts_dotted_filenames(self):
        p = 'data/profiles/user.v2.json'
        assert str(Safe_Str__Vault_Path(p)) == p

    def test__replaces_disallowed_chars(self):
        assert str(Safe_Str__Vault_Path('bad path!')) == 'bad_path_'
