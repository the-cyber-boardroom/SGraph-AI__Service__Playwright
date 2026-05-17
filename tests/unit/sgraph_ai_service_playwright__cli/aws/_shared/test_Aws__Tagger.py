# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Aws__Tagger
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Tagger              import Aws__Tagger
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Surface  import Enum__AWS__Surface


class Test__Aws__Tagger:

    def setup_method(self):
        self.tagger = Aws__Tagger()

    def test_tags_for_returns_five_tags(self):
        tags = self.tagger.tags_for(Enum__AWS__Surface.S3, 'ls')
        assert len(tags) == 5

    def test_tags_include_session_id_when_provided(self):
        tags = self.tagger.tags_for(Enum__AWS__Surface.BEDROCK, 'chat', session_id='abc123')
        assert len(tags) == 6
        keys = [str(t.key) for t in tags]
        assert 'sg:session-id' in keys

    def test_mandatory_tag_keys_present(self):
        tags = self.tagger.tags_for(Enum__AWS__Surface.EC2, 'create')
        keys = [str(t.key) for t in tags]
        for expected in ('sg:managed-by', 'sg:surface', 'sg:verb', 'sg:created-by', 'sg:created-at'):
            assert expected in keys

    def test_surface_value_written(self):
        tags = self.tagger.tags_for(Enum__AWS__Surface.FARGATE, 'task-run')
        surface_tag = next(t for t in tags if str(t.key) == 'sg:surface')
        assert str(surface_tag.value) == 's3' or str(surface_tag.value) == 'fargate'

    def test_as_boto3_tags_format(self):
        boto3_tags = self.tagger.as_boto3_tags(Enum__AWS__Surface.S3, 'bucket-create')
        assert all('Key' in t and 'Value' in t for t in boto3_tags)
