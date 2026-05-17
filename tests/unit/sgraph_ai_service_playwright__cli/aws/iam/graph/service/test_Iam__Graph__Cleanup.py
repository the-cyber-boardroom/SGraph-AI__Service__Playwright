# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Iam__Graph__Cleanup
# Verifies dry-run gate, service-linked skip, and real-delete path.
# CRITICAL: confirm=False must NEVER mutate.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service              import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name          import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request   import Schema__IAM__Role__Create__Request
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Cleanup            import Iam__Graph__Cleanup
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory import IAM__AWS__Client__In_Memory


def _candidates(*names, service_linked_names=None):
    service_linked_names = service_linked_names or set()
    return [
        dict(node_id=f'arn:aws:iam::123:role/{n}', name=n, arn=f'arn:aws:iam::123:role/{n}',
             is_service_linked=(n in service_linked_names), is_aws_default=False)
        for n in names
    ]


class Test__Iam__Graph__Cleanup:

    def test_1__dry_run_does_not_mutate(self):
        client  = IAM__AWS__Client__In_Memory()
        client.create_role(Schema__IAM__Role__Create__Request(
            role_name    = Safe_Str__IAM__Role_Name('sg-target-role'),
            trust_service= Enum__IAM__Trust__Service.LAMBDA,
        ))
        cleanup   = Iam__Graph__Cleanup(iam_client=client)
        plan      = cleanup.build_plan(_candidates('sg-target-role'))
        result    = cleanup.execute_plan(plan, confirm=False)

        assert result.dry_run is True
        assert result.executed is False
        assert result.deleted_count == 0
        # role must still exist
        assert client.role_exists('sg-target-role') is True

    def test_2__confirm_deletes_role(self):
        client = IAM__AWS__Client__In_Memory()
        client.create_role(Schema__IAM__Role__Create__Request(
            role_name    = Safe_Str__IAM__Role_Name('sg-to-delete'),
            trust_service= Enum__IAM__Trust__Service.LAMBDA,
        ))
        cleanup = Iam__Graph__Cleanup(iam_client=client)
        plan    = cleanup.build_plan(_candidates('sg-to-delete'))
        result  = cleanup.execute_plan(plan, confirm=True)

        assert result.executed is True
        assert result.deleted_count == 1
        assert result.error_count == 0
        assert client.role_exists('sg-to-delete') is False

    def test_3__service_linked_roles_skipped_in_plan(self):
        candidates = _candidates('sg-normal', 'svc-linked',
                                 service_linked_names={'svc-linked'})
        cleanup    = Iam__Graph__Cleanup()
        plan       = cleanup.build_plan(candidates)
        assert plan.skipped_service_linked == 1
        candidate_names = [n.name for n in plan.candidates]
        assert 'svc-linked' not in candidate_names
        assert 'sg-normal' in candidate_names

    def test_4__build_plan_always_dry_run(self):
        plan = Iam__Graph__Cleanup().build_plan(_candidates('sg-role'))
        assert plan.dry_run is True

    def test_5__execute_without_confirm_returns_unchanged_plan(self):
        client  = IAM__AWS__Client__In_Memory()
        client.create_role(Schema__IAM__Role__Create__Request(
            role_name    = Safe_Str__IAM__Role_Name('sg-safe-role'),
            trust_service= Enum__IAM__Trust__Service.LAMBDA,
        ))
        cleanup = Iam__Graph__Cleanup(iam_client=client)
        plan    = cleanup.build_plan(_candidates('sg-safe-role'))
        result  = cleanup.execute_plan(plan, confirm=False)
        assert result is plan                                                    # same object returned unchanged
        assert result.executed is False
