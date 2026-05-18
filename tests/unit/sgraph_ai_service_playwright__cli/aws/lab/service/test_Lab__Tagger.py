# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Tagger
# Every taggable resource type gets all 5 sg:lab:* tags + 5 canonical sg:* tags.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Tagger             import Lab__Tagger

_CANONICAL_TAG_KEYS = {'sg:managed-by', 'sg:surface', 'sg:verb', 'sg:created-by', 'sg:created-at'}
_LAB_TAG_KEYS       = {'sg:lab', 'sg:lab:run-id', 'sg:lab:experiment', 'sg:lab:resource', 'sg:lab:expires-at'}
_ALL_EXPECTED_KEYS  = _CANONICAL_TAG_KEYS | _LAB_TAG_KEYS


class test_Lab__Tagger(TestCase):

    def setUp(self):
        self.tagger = Lab__Tagger()

    def _assert_tag_keys(self, tags):
        keys = {str(t.key) for t in tags.items}
        assert keys == _ALL_EXPECTED_KEYS, f'Missing keys: {_ALL_EXPECTED_KEYS - keys}; Extra keys: {keys - _ALL_EXPECTED_KEYS}'

    def test_1__r53_record_has_10_tags(self):
        tags = self.tagger.lab_tags_for(
            run_id          = 'test-run-id',
            experiment_name = 'propagation-timeline',
            resource_type   = Enum__Lab__Resource_Type.R53_RECORD,
        )
        assert len(tags.items) == 10
        self._assert_tag_keys(tags)

    def test_2__sg_lab_tag_is_true(self):
        tags = self.tagger.lab_tags_for('r1', 'exp', Enum__Lab__Resource_Type.R53_RECORD)
        lab_tag = next((t for t in tags.items if str(t.key) == 'sg:lab'), None)
        assert lab_tag is not None
        assert str(lab_tag.value) == 'true'

    def test_3__run_id_propagated(self):
        run_id = '2026-05-18T00:00:00Z__abc123'
        tags   = self.tagger.lab_tags_for(run_id, 'exp', Enum__Lab__Resource_Type.R53_RECORD)
        tag    = next((t for t in tags.items if str(t.key) == 'sg:lab:run-id'), None)
        assert tag is not None
        assert str(tag.value) == run_id

    def test_4__experiment_name_propagated(self):
        tags = self.tagger.lab_tags_for('r', 'my-experiment', Enum__Lab__Resource_Type.CF_DISTRIBUTION)
        tag  = next((t for t in tags.items if str(t.key) == 'sg:lab:experiment'), None)
        assert tag is not None
        assert str(tag.value) == 'my-experiment'

    def test_5__resource_type_value_in_tag(self):
        tags = self.tagger.lab_tags_for('r', 'e', Enum__Lab__Resource_Type.LAMBDA)
        tag  = next((t for t in tags.items if str(t.key) == 'sg:lab:resource'), None)
        assert str(tag.value) == 'lambda'

    def test_6__expires_at_is_iso8601(self):
        tags = self.tagger.lab_tags_for('r', 'e', Enum__Lab__Resource_Type.R53_RECORD, ttl_minutes=30)
        tag  = next((t for t in tags.items if str(t.key) == 'sg:lab:expires-at'), None)
        assert tag is not None
        expires_at = str(tag.value)
        assert 'T' in expires_at
        assert expires_at.endswith('Z')

    def test_7__boto3_tags_list_format(self):
        boto3_tags = self.tagger.as_boto3_lab_tags('r', 'e', Enum__Lab__Resource_Type.R53_RECORD)
        assert isinstance(boto3_tags, list)
        assert len(boto3_tags) == 10
        for tag in boto3_tags:
            assert 'Key' in tag
            assert 'Value' in tag

    def test_8__all_resource_types_produce_10_tags(self):
        for rt in Enum__Lab__Resource_Type:
            tags = self.tagger.lab_tags_for('run', 'exp', rt)
            assert len(tags.items) == 10, f'{rt} produced {len(tags.items)} tags'
