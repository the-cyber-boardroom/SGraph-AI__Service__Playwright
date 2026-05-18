# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__ECR__Scan_Findings + Schema__ECR__Scan_Finding_Counts
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status import Enum__ECR__Image_Scan_Status
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Scan_Finding_Counts import Schema__ECR__Scan_Finding_Counts
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Scan_Findings     import Schema__ECR__Scan_Findings


_DIGEST = 'sha256:' + 'c' * 64


class Test__Schema__ECR__Scan_Finding_Counts:

    def test_1__defaults(self):
        c = Schema__ECR__Scan_Finding_Counts()
        assert c.critical      == 0
        assert c.high          == 0
        assert c.medium        == 0
        assert c.low           == 0
        assert c.informational == 0
        assert c.undefined     == 0

    def test_2__round_trip(self):
        c     = Schema__ECR__Scan_Finding_Counts(critical=1, high=2, medium=3,
                                                 low=4, informational=5, undefined=6)
        clone = Schema__ECR__Scan_Finding_Counts.from_json(c.json())
        assert clone.critical == 1
        assert clone.high     == 2
        assert clone.medium   == 3
        assert clone.low      == 4


class Test__Schema__ECR__Scan_Findings:

    def test_1__round_trip(self):
        s = Schema__ECR__Scan_Findings(
            repo_name    = Safe_Str__ECR__Repo_Name('alpha'),
            digest       = Safe_Str__ECR__Image_Digest(_DIGEST),
            status       = Enum__ECR__Image_Scan_Status.COMPLETE,
            completed_at = '2026-05-18T00:00:00+00:00',
            counts       = Schema__ECR__Scan_Finding_Counts(critical=1, high=2),
        )
        clone = Schema__ECR__Scan_Findings.from_json(s.json())
        assert str(clone.repo_name)  == 'alpha'
        assert str(clone.digest)     == _DIGEST
        assert clone.status          == Enum__ECR__Image_Scan_Status.COMPLETE
        assert clone.counts.critical == 1
        assert clone.counts.high     == 2
