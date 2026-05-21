# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — aws shared auth: AWS__Role__Profiles
# The el-lets-cf family self-registers; assert lookup, the rendered IAM policy
# document, the trust policy, and the role ARN. Pure — no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.auth import AWS__Role__Profiles as reg


class test_AWS__Role__Profiles(TestCase):

    def test_el_lets_cf_registered(self):
        assert 'el-lets-cf' in reg.all_families()
        p = reg.get_profile('el-lets-cf')
        assert p is not None
        assert p.role_name == 'sg-lets-cf'
        assert len(p.statements) == 4

    def test_unknown_family(self):
        assert reg.get_profile('does-not-exist') is None

    def test_policy_document(self):
        doc = reg.policy_document(reg.get_profile('el-lets-cf'))
        assert doc['Version'] == '2012-10-17'
        actions = {a for s in doc['Statement'] for a in s['Action']}
        for needed in ('s3:ListBucket', 's3:GetObject', 's3:PutObject',
                       'cloudfront:ListDistributions', 'logs:DescribeLogGroups',
                       'firehose:ListDeliveryStreams', 'firehose:DescribeDeliveryStream'):
            assert needed in actions, needed
        # the CF logs bucket ARN is targeted, scoped to the realtime prefix for reads
        read = next(s for s in doc['Statement'] if s['Sid'] == 'CfLogsRead')
        assert read['Resource'][0].endswith('/cloudfront-realtime/*')

    def test_trust_and_arn(self):
        trust = reg.trust_policy_document('745506449035')
        assert trust['Statement'][0]['Principal']['AWS'] == 'arn:aws:iam::745506449035:root'
        assert reg.role_arn(reg.get_profile('el-lets-cf'), '745506449035') == 'arn:aws:iam::745506449035:role/sg-lets-cf'
