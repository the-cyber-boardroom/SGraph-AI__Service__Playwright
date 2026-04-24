# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SP__CLI__Lambda__Role
# Creates (or reuses) the IAM execution role for the SP CLI Lambda and attaches
# the five inline policy documents defined in SP__CLI__Lambda__Policy. Uses
# osbot-aws's IAM_Role wrapper so we never touch boto3 directly here.
#
# Inline policies (put_role_policy) — NOT customer-managed policies
# ─────────────────────────────────────────────────────────────────
# Each policy document is attached inline to the role rather than materialised
# as a standalone IAM::Policy resource. Rationale:
#
#   • Permissions surface is smaller — the CI user only needs
#     `iam:PutRolePolicy` (per-role) rather than `iam:CreatePolicy` +
#     `iam:AttachRolePolicy` (account-level).
#   • No orphan cleanup: deleting the role also removes the policies.
#   • put_role_policy is naturally idempotent (upsert).
#   • The AWS-managed AWSLambdaBasicExecutionRole is still attached via
#     role_policy_attach — that one is not a customer resource either, so
#     no extra permission is needed for it.
#
# ensure() is idempotent: safe to re-run on every deploy.
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
POLICY_NAME__S3          = 'sp-cli-agentic-code-read'                               # s3:GetObject on the agentic code zip bucket; required for Agentic_Code_Loader cold-start hot-swap


class SP__CLI__Lambda__Role(Type_Safe):

    def ensure(self) -> dict:                                                       # Idempotent — call on every deploy
        account = AWS_Config().aws_session_account_id()
        policy  = SP__CLI__Lambda__Policy(aws_account=account)
        role    = IAM_Role(role_name=ROLE_NAME)

        if role.not_exists():                                                       # First-time provision — uses the IAM_Role helper that wraps statement-building for us (same pattern ensure_instance_profile uses for playwright-ec2)
            role.create_for_service__assume_role(ASSUME_ROLE_SERVICE)

        role.iam.role_policy_attach(LAMBDA_EXEC_MANAGED_ARN)                        # Attach the AWS-managed policy — idempotent; attaches by ARN (no CreatePolicy needed)

        inline_policies = {POLICY_NAME__EC2: policy.document_ec2_management () ,    # Inline policies: put_role_policy is an upsert; no CreatePolicy needed
                           POLICY_NAME__IAM: policy.document_iam_passrole    () ,
                           POLICY_NAME__ECR: policy.document_ecr_read        () ,
                           POLICY_NAME__STS: policy.document_sts_helpers     () ,
                           POLICY_NAME__OBS: policy.document_observability   () ,
                           POLICY_NAME__S3 : policy.document_agentic_code_read()}
        for policy_name, document in inline_policies.items():
            role.iam.role_policy_add(policy_name=policy_name, policy_document=json_dumps(document))

        return {'role_name'       : ROLE_NAME                       ,
                'role_arn'        : role.arn()                       ,
                'managed_arn'     : LAMBDA_EXEC_MANAGED_ARN          ,
                'inline_policies' : sorted(inline_policies.keys())   }

    def role_arn(self) -> str:
        return IAM_Role(role_name=ROLE_NAME).arn()

    def exists(self) -> bool:
        return IAM_Role(role_name=ROLE_NAME).exists()
