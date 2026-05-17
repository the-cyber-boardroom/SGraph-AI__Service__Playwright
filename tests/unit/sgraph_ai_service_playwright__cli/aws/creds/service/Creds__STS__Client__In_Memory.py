# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Creds__STS__Client__In_Memory
# Fake STS client for unit tests. Returns deterministic fake creds without
# making any AWS API calls.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
from datetime import datetime, timezone, timedelta

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__STS__Client import Creds__STS__Client


class _Fake_STS_Client:                                                        # Minimal boto3-alike STS client backed by in-memory dict

    def __init__(self, caller_arn: str):
        self._caller_arn = caller_arn

    def assume_role(self, RoleArn='', RoleSessionName='', DurationSeconds=3600, **_):
        expiry = datetime.now(timezone.utc) + timedelta(seconds=DurationSeconds)
        creds  = {
            'AccessKeyId'     : f'ASIA{secrets.token_hex(8).upper()}',
            'SecretAccessKey' : secrets.token_hex(20),
            'SessionToken'    : f'FwoGZXIvYXdz{secrets.token_hex(40)}',
            'Expiration'      : expiry,
        }
        return {'Credentials': creds, 'AssumedRoleUser': {'Arn': RoleArn}}

    def get_caller_identity(self):
        return {'Arn': self._caller_arn, 'Account': '123456789012', 'UserId': 'AIDAEXAMPLE'}


class Creds__STS__Client__In_Memory(Creds__STS__Client):

    caller_arn : str = 'arn:aws:iam::123456789012:user/test-user'

    def client(self):
        return _Fake_STS_Client(self.caller_arn)
