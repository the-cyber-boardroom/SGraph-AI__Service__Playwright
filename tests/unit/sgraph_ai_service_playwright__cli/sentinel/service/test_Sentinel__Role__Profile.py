# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Role__Profile (incl. the L@E service-principal trust)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.auth                          import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Role__Profile  import EDGE_FAMILY, FAMILY


class TestRegistration:
    def test_operator_profile_registered(self):
        p = profiles.get_profile(FAMILY)
        assert p is not None
        assert str(p.role_name) == 'sg-sentinel'

    def test_edge_profile_registered(self):
        p = profiles.get_profile(EDGE_FAMILY)
        assert p is not None
        assert str(p.role_name) == 'sg-sentinel-edge'


class TestOperatorTrustIsAccountRoot:
    def test_operator_uses_account_root_assume_role(self):
        p     = profiles.get_profile(FAMILY)
        trust = profiles.trust_policy_for(p, '123456789012')
        assert trust['Statement'][0]['Principal'] == {'AWS': 'arn:aws:iam::123456789012:root'}


class TestEdgeTrustIsServicePrincipal:
    def test_edge_trust_includes_both_lambda_principals(self):
        p     = profiles.get_profile(EDGE_FAMILY)
        trust = profiles.trust_policy_for(p, '123456789012')
        services = trust['Statement'][0]['Principal']['Service']
        assert 'lambda.amazonaws.com'     in services
        assert 'edgelambda.amazonaws.com' in services                                # required for Lambda@Edge

    def test_edge_profile_can_put_log_objects(self):
        p       = profiles.get_profile(EDGE_FAMILY)
        actions = [str(a) for s in p.statements for a in s.actions]
        assert 's3:PutObject' in actions


class TestPolicyDocument:
    def test_operator_policy_has_passrole_for_edge_role(self):
        p   = profiles.get_profile(FAMILY)
        doc = profiles.policy_document(p)
        actions = [a for s in doc['Statement'] for a in s['Action']]
        assert 'iam:PassRole'           in actions
        assert 'cloudfront:CreateFunction' in actions
        assert 'lambda:PublishVersion'  in actions
