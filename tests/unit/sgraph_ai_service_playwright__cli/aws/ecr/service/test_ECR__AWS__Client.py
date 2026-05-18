# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ECR__AWS__Client (in-memory)
# Unit tests for list_repositories / describe_repository / list_images /
# describe_image / get_image_scan_findings. No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, timezone

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status import Enum__ECR__Image_Scan_Status
from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory import ECR__AWS__Client__In_Memory


class Test__ECR__AWS__Client:

    # ── repositories ─────────────────────────────────────────────────────────

    def test_1__list_repositories_empty(self):
        client = ECR__AWS__Client__In_Memory()
        repos  = client.list_repositories()
        assert len(repos) == 0

    def test_2__list_repositories_returns_seeded(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha', scan_on_push=True)
        client.seed_repo('beta')
        repos = client.list_repositories()
        names = sorted(str(r.name) for r in repos)
        assert names == ['alpha', 'beta']
        alpha = next(r for r in repos if str(r.name) == 'alpha')
        assert alpha.scan_on_push is True

    def test_3__describe_repository_missing(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.describe_repository('no-such') is None

    def test_4__describe_repository_with_images_aggregates(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('myrepo')
        client.seed_image('myrepo', tags=['v1'], size=1000)
        client.seed_image('myrepo', tags=['v2'], size=2000)
        repo = client.describe_repository('myrepo')
        assert repo is not None
        assert str(repo.name)          == 'myrepo'
        assert repo.image_count        == 2
        assert repo.total_size_bytes   == 3000
        assert repo.lifecycle_policy   == ''

    def test_5__describe_repository_with_lifecycle_policy(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('with-policy')
        client.set_lifecycle_policy('with-policy', '{"rules":[]}')
        repo = client.describe_repository('with-policy')
        assert repo is not None
        assert repo.lifecycle_policy == '{"rules":[]}'

    def test_6__describe_repository_no_images(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('empty-repo')
        repo = client.describe_repository('empty-repo')
        assert repo is not None
        assert repo.image_count      == 0
        assert repo.total_size_bytes == 0

    # ── images ───────────────────────────────────────────────────────────────

    def test_7__list_images_missing_repo(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.list_images('no-such') is None

    def test_8__list_images_returns_seeded(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        client.seed_image('repo1', tags=['v1'], size=500)
        client.seed_image('repo1', tags=[],     size=700)                        # untagged
        images = client.list_images('repo1')
        assert len(images) == 2

    def test_9__list_images_untagged_filter(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        client.seed_image('repo1', tags=['v1'])
        client.seed_image('repo1', tags=[])
        untagged = client.list_images('repo1', untagged=True)
        assert len(untagged) == 1
        assert list(untagged[0].tags) == []

    def test_10__describe_image_by_tag(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        digest = client.seed_image('repo1', tags=['v1'], size=999)
        img    = client.describe_image('repo1', 'v1')
        assert img is not None
        assert str(img.digest)    == digest
        assert img.size_bytes     == 999
        assert [str(t) for t in img.tags] == ['v1']

    def test_11__describe_image_by_digest(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        digest = client.seed_image('repo1', tags=['v1'])
        img    = client.describe_image('repo1', digest)
        assert img is not None
        assert str(img.digest) == digest

    def test_12__describe_image_missing_repo(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.describe_image('no-such', 'v1') is None

    def test_13__describe_image_missing_tag(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        assert client.describe_image('repo1', 'no-such-tag') is None

    # ── scan findings ────────────────────────────────────────────────────────

    def test_14__get_image_scan_findings_complete(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        digest = client.seed_image('repo1', tags=['v1'], scan=dict(
            status       = 'COMPLETE',
            completed_at = datetime.now(timezone.utc) - timedelta(hours=1),
            counts       = {'CRITICAL': 1, 'HIGH': 2, 'MEDIUM': 3, 'LOW': 4,
                            'INFORMATIONAL': 5, 'UNDEFINED': 6},
        ))
        findings = client.get_image_scan_findings('repo1', 'v1')
        assert findings is not None
        assert findings.status               == Enum__ECR__Image_Scan_Status.COMPLETE
        assert str(findings.digest)          == digest
        assert findings.counts.critical      == 1
        assert findings.counts.high          == 2
        assert findings.counts.medium        == 3
        assert findings.counts.low           == 4
        assert findings.counts.informational == 5
        assert findings.counts.undefined     == 6

    def test_15__get_image_scan_findings_missing_image(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        assert client.get_image_scan_findings('repo1', 'no-such') is None

    def test_16__get_image_scan_findings_no_scan(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('repo1')
        client.seed_image('repo1', tags=['v1'], scan=None)
        assert client.get_image_scan_findings('repo1', 'v1') is None

    def test_17__get_image_scan_findings_missing_repo(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.get_image_scan_findings('no-such', 'v1') is None
