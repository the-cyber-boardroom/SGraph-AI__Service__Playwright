# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Creds__STS__Client (in-memory)
# No mocks. No patches. Uses Creds__STS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.creds.service.Creds__STS__Client__In_Memory import (
    Creds__STS__Client__In_Memory,
)


class Test__Creds__STS__Client:

    def test_1__assume_role_returns_all_keys(self):
        client = Creds__STS__Client__In_Memory()
        result = client.assume_role('arn:aws:iam::123456789012:role/Dev', 'test', 3600)
        assert 'AccessKeyId'     in result
        assert 'SecretAccessKey' in result
        assert 'SessionToken'    in result
        assert 'Expiration'      in result

    def test_2__access_key_id_has_aws_prefix(self):
        client = Creds__STS__Client__In_Memory()
        result = client.assume_role('arn:aws:iam::1:role/R', 'session', 900)
        assert result['AccessKeyId'].startswith('ASIA')

    def test_3__expiration_reflects_duration(self):
        from datetime import datetime, timezone
        client  = Creds__STS__Client__In_Memory()
        before  = datetime.now(timezone.utc)
        result  = client.assume_role('arn:aws:iam::1:role/R', 'session', 3600)
        expiry  = datetime.fromisoformat(result['Expiration'])
        elapsed = (expiry - before).total_seconds()
        assert 3590 < elapsed < 3610                                           # within 10s of 1h from now

    def test_4__two_calls_produce_different_keys(self):
        client = Creds__STS__Client__In_Memory()
        r1 = client.assume_role('arn:aws:iam::1:role/R', 's1', 3600)
        r2 = client.assume_role('arn:aws:iam::1:role/R', 's2', 3600)
        assert r1['AccessKeyId'] != r2['AccessKeyId']

    def test_5__get_caller_identity_returns_arn(self):
        client = Creds__STS__Client__In_Memory()
        arn    = client.get_caller_identity()
        assert arn == 'arn:aws:iam::123456789012:user/test-user'

    def test_6__short_duration_produces_earlier_expiry(self):
        from datetime import datetime, timezone
        client    = Creds__STS__Client__In_Memory()
        result_1h = client.assume_role('arn:aws:iam::1:role/R', 's1', 3600)
        result_5m = client.assume_role('arn:aws:iam::1:role/R', 's2', 300)
        exp_1h    = datetime.fromisoformat(result_1h['Expiration'])
        exp_5m    = datetime.fromisoformat(result_5m['Expiration'])
        assert exp_5m < exp_1h
