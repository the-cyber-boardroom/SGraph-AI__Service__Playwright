# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SP__CLI__Lambda__Role
# Creates (or reuses) the IAM execution role for the SP CLI Lambda and attaches
# the five inline policies defined in SP__CLI__Lambda__Policy. Uses osbot-aws's
# IAM_Role wrapper so we never touch boto3 here.
#
# ensure() is idempotent: safe to re-run on every deploy. It creates the role
# when absent, re-creates each inline policy (attach_policy deletes + recreates
# so subsequent runs pick up policy-document changes), and attaches the
# managed AWSLambdaBasicExecutionRole policy for CloudWatch logs.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_aws.aws.iam.IAM_Role                                                     import IAM_Role

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.utils.Json                                                         import json_dumps

from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Policy               import SP__CLI__Lambda__Policy


ROLE_NAME                = 'sp-playwright-cli-lambda'
ASSUME_ROLE_SERVICE      = 'lambda.amazonaws.com'                                   # Only the Lambda service can assume this role
LAMBDA_EXEC_MANAGED_ARN  = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
POLICY_NAME__EC2         = 'sp-cli-ec2-management'
POLICY_NAME__IAM         = 'sp-cli-iam-passrole'
POLICY_NAME__ECR         = 'sp-cli-ecr-read'
POLICY_NAME__STS         = 'sp-cli-sts-helpers'
POLICY_NAME__OBS         = 'sp-cli-observability'


class SP__CLI__Lambda__Role(Type_Safe):

    def ensure(self) -> dict:                                                       # Idempotent — call on every deploy
        account = AWS_Config().aws_session_account_id()
        policy  = SP__CLI__Lambda__Policy(aws_account=account)
        role    = IAM_Role(role_name=ROLE_NAME)

        if role.not_exists():                                                       # First-time provision — uses the IAM_Role helper that wraps statement-building for us (matches ensure_instance_profile's pattern for playwright-ec2)
            role.create_for_service__assume_role(ASSUME_ROLE_SERVICE)

        role.iam.role_policy_attach(LAMBDA_EXEC_MANAGED_ARN)                        # Managed policy — idempotent; no-op if already attached

        ec2_arn = role.attach_policy(POLICY_NAME__EC2, json_dumps(policy.document_ec2_management()))
        iam_arn = role.attach_policy(POLICY_NAME__IAM, json_dumps(policy.document_iam_passrole   ()))
        ecr_arn = role.attach_policy(POLICY_NAME__ECR, json_dumps(policy.document_ecr_read        ()))
        sts_arn = role.attach_policy(POLICY_NAME__STS, json_dumps(policy.document_sts_helpers     ()))
        obs_arn = role.attach_policy(POLICY_NAME__OBS, json_dumps(policy.document_observability   ()))

        return {'role_name'    : ROLE_NAME                       ,
                'role_arn'     : role.arn()                      ,
                'managed_arn'  : LAMBDA_EXEC_MANAGED_ARN          ,
                'policy_arns'  : {POLICY_NAME__EC2: ec2_arn      ,
                                  POLICY_NAME__IAM: iam_arn      ,
                                  POLICY_NAME__ECR: ecr_arn      ,
                                  POLICY_NAME__STS: sts_arn      ,
                                  POLICY_NAME__OBS: obs_arn     }}

    def role_arn(self) -> str:
        return IAM_Role(role_name=ROLE_NAME).arn()

    def exists(self) -> bool:
        return IAM_Role(role_name=ROLE_NAME).exists()
