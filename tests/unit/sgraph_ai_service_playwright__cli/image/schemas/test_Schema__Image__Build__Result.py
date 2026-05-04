# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Image__Build__Result
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Result    import Schema__Image__Build__Result


class test_Schema__Image__Build__Result(TestCase):

    def test__defaults(self):
        result = Schema__Image__Build__Result()
        assert str(result.image_id)        == ''
        assert list(result.image_tags)     == []
        assert result.duration_ms          == 0

    def test__round_trip_via_json(self):
        result = Schema__Image__Build__Result(image_id='sha256:abc',
                                              image_tags=['ecr/img:latest', 'ecr/img:v1'],
                                              duration_ms=12345)
        again  = Schema__Image__Build__Result.from_json(result.json())
        assert str(again.image_id)         == 'sha256:abc'
        assert list(again.image_tags)      == ['ecr/img:latest', 'ecr/img:v1']
        assert again.duration_ms           == 12345
