# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__ECR__Image (round-trip)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status import Enum__ECR__Image_Scan_Status
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Tag          import Safe_Str__ECR__Tag
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Image             import Schema__ECR__Image


_DIGEST = 'sha256:' + 'b' * 64


class Test__Schema__ECR__Image:

    def test_1__defaults(self):
        s = Schema__ECR__Image()
        assert str(s.repo_name)  == ''
        assert str(s.digest)     == ''
        assert list(s.tags)      == []
        assert s.size_bytes      == 0
        assert s.scan_status     == Enum__ECR__Image_Scan_Status.UNKNOWN

    def test_2__round_trip_json(self):
        s = Schema__ECR__Image(
            repo_name   = Safe_Str__ECR__Repo_Name('alpha'),
            digest      = Safe_Str__ECR__Image_Digest(_DIGEST),
            tags        = [Safe_Str__ECR__Tag('v1'), Safe_Str__ECR__Tag('latest')],
            size_bytes  = 1234,
            scan_status = Enum__ECR__Image_Scan_Status.COMPLETE,
        )
        clone = Schema__ECR__Image.from_json(s.json())
        assert str(clone.repo_name)        == 'alpha'
        assert str(clone.digest)           == _DIGEST
        assert [str(t) for t in clone.tags] == ['v1', 'latest']
        assert clone.size_bytes            == 1234
        assert clone.scan_status           == Enum__ECR__Image_Scan_Status.COMPLETE
