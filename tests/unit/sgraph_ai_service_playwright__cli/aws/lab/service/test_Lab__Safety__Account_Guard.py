# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Safety__Account_Guard
# In-memory STS fake; env-var unset → no-op; mismatch → raises.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Safety__Account_Guard import Lab__Safety__Account_Guard

_ENV_EXPECTED = 'SG_AWS__LAB__EXPECTED_ACCOUNT_ID'


class _Fake_Guard(Lab__Safety__Account_Guard):

    def get_identity(self):
        from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Account_Id import Safe_Str__AWS__Account_Id
        from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN        import Safe_Str__AWS__ARN
        from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region     import Safe_Str__AWS__Region
        from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Account__Identity   import Schema__Lab__Account__Identity
        return Schema__Lab__Account__Identity(
            account_id = Safe_Str__AWS__Account_Id('123456789012'),
            user_id    = 'AIDAEXAMPLE',
            arn        = Safe_Str__AWS__ARN('arn:aws:iam::123456789012:user/test'),
            region     = Safe_Str__AWS__Region('us-east-1'),
        )


class test_Lab__Safety__Account_Guard(TestCase):

    def setUp(self):
        os.environ.pop(_ENV_EXPECTED, None)                                        # start clean

    def tearDown(self):
        os.environ.pop(_ENV_EXPECTED, None)

    def test_1__no_env_var_is_noop(self):
        guard    = _Fake_Guard()
        identity = guard.check()
        assert str(identity.account_id) == '123456789012'                         # no exception raised

    def test_2__matching_account_passes(self):
        os.environ[_ENV_EXPECTED] = '123456789012'
        guard    = _Fake_Guard()
        identity = guard.check()
        assert str(identity.account_id) == '123456789012'

    def test_3__mismatching_account_raises(self):
        os.environ[_ENV_EXPECTED] = '999999999999'
        guard = _Fake_Guard()
        with self.assertRaises(ValueError) as ctx:
            guard.check()
        assert '999999999999' in str(ctx.exception)
        assert '123456789012' in str(ctx.exception)

    def test_4__set_expected_updates_env(self):
        guard = _Fake_Guard()
        guard.set_expected('111111111111')
        assert os.environ.get(_ENV_EXPECTED) == '111111111111'

    def test_5__get_identity_returns_schema(self):
        from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Account__Identity import Schema__Lab__Account__Identity
        guard    = _Fake_Guard()
        identity = guard.get_identity()
        assert isinstance(identity, Schema__Lab__Account__Identity)
        assert str(identity.region) == 'us-east-1'
