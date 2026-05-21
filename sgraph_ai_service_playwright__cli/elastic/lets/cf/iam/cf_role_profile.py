# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf iam: cf_role_profile
# The least-privilege role profile for the `sg el lets cf *` command family. This is
# the per-section footprint the reuse contract promises: declare what the family needs
# and self-register it. The generic engine (aws/_shared/auth) does everything else —
# create/assume/diff. Actions enumerated from every cf_app command (see the plan doc).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Profiles            import register
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Policy__Statement import Schema__AWS__Policy__Statement
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Role__Profile     import Schema__AWS__Role__Profile
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config             import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION

FAMILY      = 'el-lets-cf'
ROLE_NAME   = 'sg-lets-cf'
_BUCKET_ARN = f'arn:aws:s3:::{CF_LOGS_BUCKET}'
_ACCOUNT    = CF_LOGS_BUCKET.split('--', 1)[0]                                        # 745506449035 prefixes the bucket name


def build_profile() -> Schema__AWS__Role__Profile:
    profile = Schema__AWS__Role__Profile(family=FAMILY, role_name=ROLE_NAME,
                                         description='Least-privilege role for the sg el lets cf command family.')
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='CfLogsList', actions=['s3:ListBucket'], resources=[_BUCKET_ARN]))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='CfLogsRead', actions=['s3:GetObject'], resources=[f'{_BUCKET_ARN}/{CF_LOGS_PREFIX}*']))
    profile.statements.append(Schema__AWS__Policy__Statement(                         # consolidate C-stage only — its own statement so read-only operators can drop it
        sid='CfLogsConsolidateWrite', actions=['s3:PutObject'], resources=[f'{_BUCKET_ARN}/lets/*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='CfArchRead',
        actions=['cloudfront:ListDistributions', 'logs:DescribeLogGroups',
                 'firehose:ListDeliveryStreams', 'firehose:DescribeDeliveryStream'],
        resources=['*']))
    return profile


register(build_profile())
