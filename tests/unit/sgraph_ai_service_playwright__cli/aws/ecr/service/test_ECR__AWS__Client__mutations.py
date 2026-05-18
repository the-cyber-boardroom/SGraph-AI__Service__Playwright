# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ECR__AWS__Client mutations
# Exercise delete_image, batch_delete_images, create_repository, delete_repository
# against the in-memory fake. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from botocore.exceptions import ClientError

from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory import ECR__AWS__Client__In_Memory


class Test__ECR__AWS__Client__Mutations:

    # ── delete_image ─────────────────────────────────────────────────────────

    def test_1__delete_image_by_tag(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        assert client.delete_image('alpha', 'v1') is True
        # confirm gone
        assert client.describe_image('alpha', 'v1') is None

    def test_2__delete_image_by_digest(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        digest = client.seed_image('alpha', tags=['v1'])
        assert client.delete_image('alpha', digest) is True
        assert client.describe_image('alpha', digest) is None

    def test_3__delete_image_missing_returns_false(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        assert client.delete_image('alpha', 'does-not-exist') is False

    def test_4__delete_image_missing_repo_returns_false(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.delete_image('nope', 'v1') is False

    # ── batch_delete_images ──────────────────────────────────────────────────

    def test_5__batch_delete_images_returns_count(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        d1 = client.seed_image('alpha', tags=['v1'])
        d2 = client.seed_image('alpha', tags=['v2'])
        n = client.batch_delete_images('alpha', [d1, d2])
        assert n == 2
        assert client.list_images('alpha') == []

    def test_6__batch_delete_images_empty_list_returns_zero(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        assert client.batch_delete_images('alpha', []) == 0

    def test_7__batch_delete_images_partial_misses(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        d1 = client.seed_image('alpha', tags=['v1'])
        n = client.batch_delete_images('alpha', [d1, 'sha256:bogus'])
        assert n == 1

    def test_8__batch_delete_images_missing_repo_returns_zero(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.batch_delete_images('nope', ['sha256:abc']) == 0

    # ── create_repository ────────────────────────────────────────────────────

    def test_9__create_repository_new(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.create_repository('brand-new') is True
        # confirm exists
        repo = client.describe_repository('brand-new')
        assert repo is not None
        assert str(repo.name) == 'brand-new'

    def test_10__create_repository_already_exists_returns_false(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        assert client.create_repository('alpha') is False

    # ── delete_repository ────────────────────────────────────────────────────

    def test_11__delete_repository_empty(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        assert client.delete_repository('alpha') is True
        assert client.describe_repository('alpha') is None

    def test_12__delete_repository_missing_returns_false(self):
        client = ECR__AWS__Client__In_Memory()
        assert client.delete_repository('nope') is False

    def test_13__delete_repository_not_empty_raises(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        with pytest.raises(ClientError) as exc_info:
            client.delete_repository('alpha', force=False)
        assert exc_info.value.response['Error']['Code'] == 'RepositoryNotEmptyException'

    def test_14__delete_repository_with_force_succeeds(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        assert client.delete_repository('alpha', force=True) is True
        assert client.describe_repository('alpha') is None
