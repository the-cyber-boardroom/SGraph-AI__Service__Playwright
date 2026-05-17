# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__Stop__Policy__Template
# Typed policy for an operator role that can stop/start vault-app EC2 instances.
# Tag-conditioned to prevent unscoped stop/start on arbitrary instances.
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


class Vault_App__Stop__Policy__Template(Type_Safe):

    def build(self) -> Schema__IAM__Policy:
        describe_actions = List__Safe_Str__Aws__Action()
        describe_actions.append(Safe_Str__Aws__Action('ec2:DescribeInstances'))
        describe_resources = List__Safe_Str__Aws__Resource()
        describe_resources.append(Safe_Str__Aws__Resource('*'))

        stop_start_actions = List__Safe_Str__Aws__Action()
        for a in ['ec2:StopInstances', 'ec2:StartInstances']:
            stop_start_actions.append(Safe_Str__Aws__Action(a))
        stop_start_resources = List__Safe_Str__Aws__Resource()
        stop_start_resources.append(Safe_Str__Aws__Resource('arn:aws:ec2:*:*:instance/*'))
        condition = json.dumps({'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}})

        stmts = List__Schema__IAM__Statement()
        stmts.append(Schema__IAM__Statement(
            effect                  = 'Allow',
            actions                 = describe_actions,
            resources               = describe_resources,
            allow_wildcard_resource = True,              # EC2 Describe has no resource-level perms
        ))
        stmts.append(Schema__IAM__Statement(
            effect         = 'Allow',
            actions        = stop_start_actions,
            resources      = stop_start_resources,
            condition_json = condition,
        ))
        return Schema__IAM__Policy(statements=stmts)
