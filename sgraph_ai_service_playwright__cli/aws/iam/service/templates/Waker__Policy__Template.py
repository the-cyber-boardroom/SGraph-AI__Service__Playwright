# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Waker__Policy__Template
# Typed policy document for the vault-publish Waker Lambda execution role.
# Reflects the manual policy from §0.5 of the v0.2.23 test guide.
#
# Audit target state: max INFO (0 WARN, 0 CRITICAL).
#   • CloudWatch logs  — wildcard resource accepted (logs: no resource-level perms)
#   • EC2 Describe     — wildcard resource accepted (AWS limitation)
#   • EC2 StartInstances — narrow ARN + tag condition (no wildcard resource flag)
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


class Waker__Policy__Template(Type_Safe):

    def build(self) -> Schema__IAM__Policy:
        logs_actions   = List__Safe_Str__Aws__Action()
        for a in ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents']:
            logs_actions.append(Safe_Str__Aws__Action(a))
        logs_resources = List__Safe_Str__Aws__Resource()
        logs_resources.append(Safe_Str__Aws__Resource('arn:aws:logs:*:*:*'))

        ec2_describe_actions   = List__Safe_Str__Aws__Action()
        ec2_describe_actions.append(Safe_Str__Aws__Action('ec2:DescribeInstances'))
        ec2_describe_resources = List__Safe_Str__Aws__Resource()
        ec2_describe_resources.append(Safe_Str__Aws__Resource('*'))

        ec2_start_actions   = List__Safe_Str__Aws__Action()
        ec2_start_actions.append(Safe_Str__Aws__Action('ec2:StartInstances'))
        ec2_start_resources = List__Safe_Str__Aws__Resource()
        ec2_start_resources.append(Safe_Str__Aws__Resource('arn:aws:ec2:*:*:instance/*'))
        ec2_start_condition = json.dumps({'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}})

        stmts = List__Schema__IAM__Statement()
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = logs_actions,
            resources               = logs_resources,
            allow_wildcard_resource = True,              # accepted exception — logs has no resource-level perms
        ))
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = ec2_describe_actions,
            resources               = ec2_describe_resources,
            allow_wildcard_resource = True,              # accepted exception — EC2 Describe has no resource-level perms
        ))
        stmts.append(Schema__IAM__Statement(
            effect         = 'Allow',
            actions        = ec2_start_actions,
            resources      = ec2_start_resources,
            condition_json = ec2_start_condition,        # tag condition prevents unscoped StartInstances
        ))
        return Schema__IAM__Policy(statements=stmts)
