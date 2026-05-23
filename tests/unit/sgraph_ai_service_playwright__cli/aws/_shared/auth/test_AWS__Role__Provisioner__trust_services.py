# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the trust_services field on role profiles (option a)
# A profile with trust_services renders a service-principal (execution-role) trust;
# without it, the default account-root assume-role trust. Pure — no IAM/AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Provisioner             import AWS__Role__Provisioner
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Role__Profile import Schema__AWS__Role__Profile


def _profile(trust_services=None) -> Schema__AWS__Role__Profile:
    p = Schema__AWS__Role__Profile(family='x', role_name='r', description='d')
    for s in (trust_services or []):
        p.trust_services.append(s)
    return p


class TestDefaultAccountRootTrust:
    def test_no_trust_services_uses_account_root(self):
        trust = json.loads(AWS__Role__Provisioner().desired_trust_json('123456789012', _profile()))
        assert trust['Statement'][0]['Principal'] == {'AWS': 'arn:aws:iam::123456789012:root'}


class TestServiceTrust:
    def test_trust_services_render_service_principals(self):
        p     = _profile(['lambda.amazonaws.com', 'edgelambda.amazonaws.com'])
        trust = json.loads(AWS__Role__Provisioner().desired_trust_json('123456789012', p))
        assert trust['Statement'][0]['Principal'] == {'Service': ['lambda.amazonaws.com', 'edgelambda.amazonaws.com']}
        assert trust['Statement'][0]['Action'] == 'sts:AssumeRole'

    def test_no_profile_arg_still_account_root(self):
        trust = json.loads(AWS__Role__Provisioner().desired_trust_json('123456789012'))
        assert 'AWS' in trust['Statement'][0]['Principal']
