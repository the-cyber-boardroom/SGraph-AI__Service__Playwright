# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Toml__Parser
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Parser import Toml__Parser


VALID_TOML = """
[roles.default]
region          = "us-east-1"
assume_role_arn = ""
session_name    = ""

[aws_credentials.default]
access_key = "AKIAIOSFODNN7EXAMPLE"
secret_key = "********"
"""

INVALID_TOML = 'this is [ not valid toml {'


class test_Toml__Parser(TestCase):

    def test_parse_valid(self):
        snap, err = Toml__Parser().parse(VALID_TOML)
        assert err  is None
        assert snap is not None
        assert 'default' in snap.roles
        assert snap.roles['default']['region'] == 'us-east-1'
        assert snap.aws_credentials['default']['access_key'] == 'AKIAIOSFODNN7EXAMPLE'
        assert snap.aws_credentials['default']['secret_key'] == '********'

    def test_parse_invalid_returns_error(self):
        snap, err = Toml__Parser().parse(INVALID_TOML)
        assert snap is None
        assert err  is not None
        assert 'TOML' in err or 'error' in err.lower()

    def test_parse_empty_string(self):
        snap, err = Toml__Parser().parse('')
        assert err  is None
        assert snap is not None
        assert snap.roles           == {}
        assert snap.aws_credentials == {}

    def test_parse_vault_keys(self):
        toml = '[vault_keys]\nmy-vault = "some-secret"\n'
        snap, err = Toml__Parser().parse(toml)
        assert err is None
        assert snap.vault_keys.get('my-vault') == 'some-secret'

    def test_parse_secrets(self):
        toml = '[secrets.my-ns]\ndb-pw = "hunter2"\n'
        snap, err = Toml__Parser().parse(toml)
        assert err is None
        assert snap.secrets.get('my-ns', {}).get('db-pw') == 'hunter2'
