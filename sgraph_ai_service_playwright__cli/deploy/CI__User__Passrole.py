# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CI/deploy-user PassRole bootstrap
# Mirrors scripts/provision_ec2.py::ensure_caller_passrole but for the SP CLI
# Lambda role. Ensures the IAM user running `provision` has iam:PassRole on
# arn:aws:iam::<account>:role/sp-playwright-cli-lambda, scoped to
# lambda.amazonaws.com.
#
# Why this exists
# ───────────────
# lambda:CreateFunction requires the CALLER (CI user) to have iam:PassRole on
# the execution role passed to the function. Without this, the first-ever
# deploy returns AccessDeniedException and we can't create the Lambda.
# Running this bootstrap once (idempotent afterwards) unblocks every future
# re-deploy without manual IAM console work.
#
# Safeguards
# ──────────
# - Skips if caller is not an IAM user (e.g. running inside a role — Lambda
#   execution context). Roles can't put_user_policy on themselves anyway.
# - ARN-pinned Resource + iam:PassedToService condition keep the grant
#   narrow: the user can only pass THIS ONE role, and only to Lambda.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import boto3

from osbot_aws.AWS_Config                                                           import AWS_Config

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Role                 import ASSUME_ROLE_SERVICE, ROLE_NAME as SP_CLI_ROLE_NAME


CI_PASSROLE_POLICY_NAME = 'sg-playwright-cli-passrole'                              # Inline policy name on the CI IAM user


class CI__User__Passrole(Type_Safe):

    def ensure(self) -> dict:                                                       # Idempotent; returns dict describing what happened
        account    = AWS_Config().aws_session_account_id()
        role_arn   = f'arn:aws:iam::{account}:role/{SP_CLI_ROLE_NAME}'
        policy_doc = json.dumps(self.build_policy_document(role_arn))

        sts        = boto3.client('sts')
        identity   = sts.get_caller_identity()
        caller_arn = identity.get('Arn', '')

        if ':user/' not in caller_arn:                                              # Lambda / federated / role — can't put_user_policy on non-users
            return {'ok'    : True,
                    'action': 'skipped',
                    'detail': f'Caller is not an IAM user ({caller_arn}) — skipping PassRole grant'}

        username = caller_arn.split(':user/')[-1]
        iam      = boto3.client('iam')
        existing = iam.list_user_policies(UserName=username).get('PolicyNames', [])
        if CI_PASSROLE_POLICY_NAME in existing:
            return {'ok'    : True,
                    'action': 'already_exists',
                    'detail': f'Policy {CI_PASSROLE_POLICY_NAME!r} already attached to {username}'}

        try:
            iam.put_user_policy(UserName     = username                ,
                                PolicyName   = CI_PASSROLE_POLICY_NAME ,
                                PolicyDocument = policy_doc            )
        except Exception as exc:
            if 'AccessDenied' in str(exc) or 'UnauthorizedOperation' in str(exc):
                return {'ok'    : False,
                        'action': 'access_denied',
                        'detail': f'User {username} cannot PutUserPolicy on itself — attach the inline policy manually. Error: {exc}'}
            raise

        return {'ok'    : True,
                'action': 'created',
                'detail': f'Attached inline policy {CI_PASSROLE_POLICY_NAME!r} to {username} (PassRole → {role_arn}, Lambda only)'}

    def build_policy_document(self, role_arn: str) -> dict:
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'      : 'PassRoleToLambdaOnly',
                               'Effect'   : 'Allow',
                               'Action'   : 'iam:PassRole',
                               'Resource' : role_arn,
                               'Condition': {'StringEquals': {'iam:PassedToService': ASSUME_ROLE_SERVICE}}}]}
