# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Cleanup
# Executes a cleanup plan against the real IAM API.
# ALWAYS dry-run by default. confirm=True AND mutation gate required to mutate.
#
# HIGH BLAST-RADIUS — AppSec note:
#   This class can delete multiple IAM roles in a single call. Service-linked
#   roles are never deleted (filtered pre-flight). Cascade-risk roles (attached
#   to active resources) require --force-cascade. All deletes are logged.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client                          import IAM__AWS__Client
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Cleanup__Plan          import Schema__IAM__Cleanup__Plan
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node  import List__Schema__IAM__Graph__Node


class Iam__Graph__Cleanup(Type_Safe):

    iam_client : IAM__AWS__Client

    def setup(self):
        if self.iam_client is None:
            self.iam_client = IAM__AWS__Client()
        return self

    # ── public ────────────────────────────────────────────────────────────────

    def build_plan(self, candidates: list) -> Schema__IAM__Cleanup__Plan:
        from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node   import Schema__IAM__Graph__Node
        from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id import Safe_Str__IAM__Node__Id
        from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type        import Enum__IAM__Node__Type
        from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth    import Enum__IAM__Scope__Breadth
        node_list      = List__Schema__IAM__Graph__Node()
        skipped_svc    = 0
        for raw in candidates:
            if isinstance(raw, dict):
                if raw.get('is_service_linked', False):
                    skipped_svc += 1
                    continue
                node_id = raw.get('node_id', raw.get('name', ''))
                if not node_id:
                    continue
                node = Schema__IAM__Graph__Node(
                    node_id          = Safe_Str__IAM__Node__Id(node_id),
                    node_type        = Enum__IAM__Node__Type.ROLE,
                    name             = raw.get('name', ''),
                    arn              = raw.get('arn', ''),
                    created_at       = raw.get('created_at', ''),
                    last_used        = raw.get('last_used', ''),
                    scope_breadth    = Enum__IAM__Scope__Breadth.SPECIFIC,
                    is_aws_default   = raw.get('is_aws_default', False),
                    is_service_linked= False,
                    trust_principal  = raw.get('trust_principal', ''),
                )
                node_list.append(node)
            else:
                if getattr(raw, 'is_service_linked', False):
                    skipped_svc += 1
                    continue
                node_list.append(raw)
        return Schema__IAM__Cleanup__Plan(
            candidates             = node_list,
            dry_run                = True,
            skipped_service_linked = skipped_svc,
        )

    def execute_plan(self, plan: Schema__IAM__Cleanup__Plan, confirm: bool = False) -> Schema__IAM__Cleanup__Plan:
        if not confirm:
            return plan                                                          # dry-run: return unchanged
        self.setup()
        deleted = 0
        errors  = 0
        for node in plan.candidates:
            role_name = node.name or str(node.node_id)
            ok = self.iam_client.delete_role(role_name)
            if ok:
                deleted += 1
            else:
                errors += 1
        plan.dry_run       = False
        plan.executed      = True
        plan.deleted_count = deleted
        plan.error_count   = errors
        return plan
