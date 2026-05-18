# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__ECR__Repo (round-trip)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Repo            import Schema__ECR__Repo


class Test__Schema__ECR__Repo:

    def test_1__defaults(self):
        s = Schema__ECR__Repo()
        assert str(s.name)               == ''
        assert s.image_count             == 0
        assert s.total_size_bytes        == 0
        assert s.scan_on_push            is False

    def test_2__round_trip_json(self):
        s = Schema__ECR__Repo(
            name             = Safe_Str__ECR__Repo_Name('alpha'),
            arn              = 'arn:aws:ecr:eu-west-2:123:repository/alpha',
            registry_id      = '123',
            image_count      = 3,
            total_size_bytes = 9000,
            scan_on_push     = True,
        )
        data  = s.json()
        clone = Schema__ECR__Repo.from_json(data)
        assert str(clone.name)        == 'alpha'
        assert clone.image_count      == 3
        assert clone.total_size_bytes == 9000
        assert clone.scan_on_push     is True
