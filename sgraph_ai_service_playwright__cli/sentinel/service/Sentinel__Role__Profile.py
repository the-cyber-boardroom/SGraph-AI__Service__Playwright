# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Role__Profile
# Self-registers the SG/Sentinel least-privilege role profiles (mirrors
# cf_role_profile). Two roles:
#   • 'sentinel'      — the operator role the CLI assumes to deploy/destroy:
#                       CF Function + distribution CRUD, Lambda CRUD + publish,
#                       S3 log-bucket ops, and iam:PassRole for the L@E exec role.
#   • 'sentinel-edge' — the Lambda@Edge EXECUTION role: trusted by both
#                       lambda.amazonaws.com and edgelambda.amazonaws.com (the
#                       trust_services field added for this), with s3:PutObject to
#                       the log bucket + CloudWatch Logs.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Profiles                     import register
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Policy__Statement  import Schema__AWS__Policy__Statement
from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Role__Profile      import Schema__AWS__Role__Profile

FAMILY            = 'sentinel'
ROLE_NAME         = 'sg-sentinel'
EDGE_FAMILY       = 'sentinel-edge'
EDGE_ROLE_NAME    = 'sg-sentinel-edge'
BUCKET_PREFIX     = 'sg-sentinel-logs'                                                # derived log buckets share this prefix
_BUCKET_ARN       = f'arn:aws:s3:::{BUCKET_PREFIX}-*'


def build_operator_profile() -> Schema__AWS__Role__Profile:
    profile = Schema__AWS__Role__Profile(family=FAMILY, role_name=ROLE_NAME,
                                         description='Operator role for the sg sentinel deploy/destroy command family.')
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelCfFunctions',
        actions=['cloudfront:CreateFunction', 'cloudfront:UpdateFunction', 'cloudfront:PublishFunction',
                 'cloudfront:DescribeFunction', 'cloudfront:GetFunction', 'cloudfront:DeleteFunction'],
        resources=['*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelCfDistribution',
        actions=['cloudfront:CreateDistribution', 'cloudfront:GetDistribution', 'cloudfront:GetDistributionConfig',
                 'cloudfront:UpdateDistribution', 'cloudfront:DeleteDistribution', 'cloudfront:ListDistributions'],
        resources=['*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelLambda',
        actions=['lambda:CreateFunction', 'lambda:UpdateFunctionCode', 'lambda:UpdateFunctionConfiguration',
                 'lambda:GetFunction', 'lambda:PublishVersion', 'lambda:DeleteFunction'],
        resources=['*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelLogBucket',
        actions=['s3:CreateBucket', 's3:PutBucketPublicAccessBlock', 's3:PutBucketVersioning',
                 's3:ListBucket', 's3:DeleteBucket'],
        resources=[_BUCKET_ARN]))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelLogObjects',
        actions=['s3:PutObject', 's3:GetObject', 's3:DeleteObject'],
        resources=[f'{_BUCKET_ARN}/*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='SentinelPassEdgeRole', actions=['iam:PassRole'],
        resources=[f'arn:aws:iam::*:role/{EDGE_ROLE_NAME}']))
    return profile


def build_edge_execution_profile() -> Schema__AWS__Role__Profile:
    profile = Schema__AWS__Role__Profile(family=EDGE_FAMILY, role_name=EDGE_ROLE_NAME,
                                         description='Lambda@Edge execution role for SG/Sentinel L2 (logging + enforcement).')
    profile.trust_services.append('lambda.amazonaws.com')                            # L@E exec-role trust (option a)
    profile.trust_services.append('edgelambda.amazonaws.com')
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='EdgeLogObjects', actions=['s3:PutObject'], resources=[f'{_BUCKET_ARN}/*']))
    profile.statements.append(Schema__AWS__Policy__Statement(
        sid='EdgeCloudWatchLogs',
        actions=['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
        resources=['arn:aws:logs:*:*:*']))
    return profile


register(build_operator_profile())
register(build_edge_execution_profile())
