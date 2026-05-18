# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Safety__Account_Guard
# Checks that the active AWS account matches SG_AWS__LAB__EXPECTED_ACCOUNT_ID.
# No-op when the env var is unset (safe on first use); raises when set and the
# actual account doesn't match. Routes through Sg__Aws__Session.from_context()
# — no boto3 import here.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Account__Identity import Schema__Lab__Account__Identity
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Account_Id import Safe_Str__AWS__Account_Id
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN        import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region     import Safe_Str__AWS__Region

_ENV_EXPECTED = 'SG_AWS__LAB__EXPECTED_ACCOUNT_ID'


class Lab__Safety__Account_Guard(Type_Safe):

    def check(self) -> Schema__Lab__Account__Identity:
        identity = self.get_identity()
        expected = os.environ.get(_ENV_EXPECTED, '').strip()
        if expected and str(identity.account_id) != expected:
            raise ValueError(
                f'Account guard: expected account {expected!r} '
                f'but got {str(identity.account_id)!r}. '
                f'Refusing to run lab mutations.'
            )
        return identity

    def get_identity(self) -> Schema__Lab__Account__Identity:
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
            session = Sg__Aws__Session.from_context()
            sts     = session.boto3_client_from_context('sts')
            resp    = sts.get_caller_identity()
            import boto3
            region  = sts.meta.region_name or boto3.session.Session().region_name or 'us-east-1'
            return Schema__Lab__Account__Identity(
                account_id = Safe_Str__AWS__Account_Id(resp.get('Account', '')),
                user_id    = resp.get('UserId', ''),
                arn        = Safe_Str__AWS__ARN(resp.get('Arn', '')),
                region     = Safe_Str__AWS__Region(region),
            )
        except Exception as ex:
            return Schema__Lab__Account__Identity(
                account_id = Safe_Str__AWS__Account_Id(''),
                user_id    = '',
                arn        = Safe_Str__AWS__ARN(''),
                region     = Safe_Str__AWS__Region(''),
            )

    def set_expected(self, account_id: str) -> None:
        os.environ[_ENV_EXPECTED] = account_id
