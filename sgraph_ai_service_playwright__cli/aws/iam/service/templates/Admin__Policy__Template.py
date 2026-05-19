# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Admin__Policy__Template
# Typed policy document for the sg-compute-vault-publish-admin Lambda execution
# role. Broader than the waker's policy because admin runs the full register /
# unpublish / adopt flows on top of the slug-inventory reads.
#
# Permission groups:
#   • CloudWatch logs       — same as waker (logs:* on logs:*:*:*)
#   • EC2 Describe          — wildcard resource (AWS limitation)
#   • EC2 RunInstances      — needed for register (provisions vault EC2s)
#   • EC2 TerminateInstances — needed for unpublish, narrow tag condition
#   • EC2 CreateTags        — needed during register (tag the new instance)
#   • EC2 StartInstances    — needed for wake-on-access from the admin UI
#   • Route 53              — needed for auto-DNS + unpublish DNS cleanup
#   • IAM PassRole          — admin Lambda assigns the waker exec role to new EC2s
#   • Lambda GetFunction*   — needed for cross-Lambda Function URL discovery
#   • SSM SendCommand       — needed for cert-renew + container ops on EC2
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Action   import List__Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Resource import List__Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Statement  import List__Schema__IAM__Statement
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Action          import Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Resource        import Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Policy               import Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement            import Schema__IAM__Statement


VAULT_APP_TAG_CONDITION = json.dumps({'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}})


def _actions(names) -> List__Safe_Str__Aws__Action:
    out = List__Safe_Str__Aws__Action()
    for n in names:
        out.append(Safe_Str__Aws__Action(n))
    return out


def _resources(arns) -> List__Safe_Str__Aws__Resource:
    out = List__Safe_Str__Aws__Resource()
    for a in arns:
        out.append(Safe_Str__Aws__Resource(a))
    return out


class Admin__Policy__Template(Type_Safe):

    def build(self) -> Schema__IAM__Policy:
        stmts = List__Schema__IAM__Statement()

        # CloudWatch logs (same as waker)
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents']),
            resources               = _resources(['arn:aws:logs:*:*:*']),
            allow_wildcard_resource = True,                                       # accepted exception — logs has no resource-level perms
        ))

        # EC2 read across regions (cross-region scan when resolving slugs).
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['ec2:DescribeInstances', 'ec2:DescribeImages',
                                                 'ec2:DescribeRegions', 'ec2:DescribeVpcs',
                                                 'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups',
                                                 'ec2:DescribeKeyPairs']),
            resources               = _resources(['*']),
            allow_wildcard_resource = True,                                       # AWS limitation — Describe has no resource-level perms
        ))

        # EC2 RunInstances — needed for register (vault-app create_stack). Narrow
        # tag condition prevents creating untagged instances; the actual EC2
        # launch is done by Vault_App__Service which we share with `sg va`.
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['ec2:RunInstances']),
            resources               = _resources([
                'arn:aws:ec2:*:*:instance/*', 'arn:aws:ec2:*:*:network-interface/*',
                'arn:aws:ec2:*:*:security-group/*', 'arn:aws:ec2:*:*:subnet/*',
                'arn:aws:ec2:*:*:volume/*', 'arn:aws:ec2:*:*:image/*',
                'arn:aws:ec2:*:*:key-pair/*',
            ]),
        ))

        # EC2 CreateTags — needed during register (set sg:slug / StackName / StackType).
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['ec2:CreateTags', 'ec2:DeleteTags']),
            resources               = _resources(['arn:aws:ec2:*:*:instance/*']),
        ))

        # EC2 Start / Stop / Terminate — wake-on-access + unpublish. Tag-scoped.
        stmts.append(Schema__IAM__Statement(
            effect         = 'Allow',
            actions        = _actions(['ec2:StartInstances', 'ec2:StopInstances', 'ec2:TerminateInstances']),
            resources      = _resources(['arn:aws:ec2:*:*:instance/*']),
            condition_json = VAULT_APP_TAG_CONDITION,
        ))

        # Security groups — create + manage for new vaults.
        stmts.append(Schema__IAM__Statement(
            effect    = 'Allow',
            actions   = _actions(['ec2:CreateSecurityGroup', 'ec2:DeleteSecurityGroup',
                                   'ec2:AuthorizeSecurityGroupIngress', 'ec2:RevokeSecurityGroupIngress']),
            resources = _resources(['arn:aws:ec2:*:*:security-group/*']),
        ))

        # Route 53 — auto-DNS upsert during register, cleanup during unpublish.
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['route53:ChangeResourceRecordSets',
                                                 'route53:GetChange',
                                                 'route53:ListHostedZones',
                                                 'route53:ListResourceRecordSets',
                                                 'route53:GetHostedZone']),
            resources               = _resources(['*']),
            allow_wildcard_resource = True,                                       # Route 53 has limited resource-level perms
        ))

        # IAM PassRole — admin Lambda passes the waker exec role to new EC2s
        # (instance profile). Tightly scoped to the known role names.
        stmts.append(Schema__IAM__Statement(
            effect    = 'Allow',
            actions   = _actions(['iam:PassRole', 'iam:GetRole', 'iam:GetInstanceProfile',
                                   'iam:CreateInstanceProfile', 'iam:AddRoleToInstanceProfile']),
            resources = _resources(['arn:aws:iam::*:role/sg-compute-vault-app-*',
                                     'arn:aws:iam::*:role/sg-compute-vault-publish-*',
                                     'arn:aws:iam::*:instance-profile/sg-compute-vault-*']),
        ))

        # Lambda introspection — needed for the admin UI to surface deployment
        # metadata about the waker (e.g. status checks).
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['lambda:GetFunction', 'lambda:GetFunctionConfiguration',
                                                 'lambda:GetFunctionUrlConfig', 'lambda:ListFunctions']),
            resources               = _resources(['arn:aws:lambda:*:*:function:sg-compute-vault-publish-*']),
        ))

        # SSM SendCommand — needed for cert-renew + container ops on running EC2s.
        # Scoped to vault-app instances via the document + tag condition.
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = _actions(['ssm:SendCommand', 'ssm:GetCommandInvocation',
                                                 'ssm:ListCommands', 'ssm:ListCommandInvocations']),
            resources               = _resources(['*']),
            allow_wildcard_resource = True,                                       # SSM SendCommand needs * on instance ARN; tag condition does the scoping
        ))

        return Schema__IAM__Policy(statements=stmts)
