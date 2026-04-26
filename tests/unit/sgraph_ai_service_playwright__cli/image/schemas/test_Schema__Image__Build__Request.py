# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Image__Build__Request
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Request   import Schema__Image__Build__Request
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item      import Schema__Image__Stage__Item


class test_Schema__Image__Build__Request(TestCase):

    def test__defaults(self):
        req = Schema__Image__Build__Request()
        assert str(req.image_folder)         == ''
        assert str(req.image_tag)            == ''
        assert list(req.stage_items)         == []
        assert str(req.dockerfile_name)      == 'dockerfile'                        # Lowercase per existing convention
        assert str(req.requirements_name)    == 'requirements.txt'
        assert str(req.build_context_prefix) == 'sg_image_build_'

    def test__round_trip_via_json_with_stage_items(self):
        item_a = Schema__Image__Stage__Item(source_path='/repo/lambda_entry.py', target_name='lambda_entry.py')
        item_b = Schema__Image__Stage__Item(source_path='/repo/pkg', target_name='pkg', is_tree=True)
        req    = Schema__Image__Build__Request(image_folder='/repo/docker/img', image_tag='ecr/img:latest', stage_items=[item_a, item_b])

        again = Schema__Image__Build__Request.from_json(req.json())
        assert str(again.image_folder)        == '/repo/docker/img'
        assert str(again.image_tag)           == 'ecr/img:latest'
        assert len(again.stage_items)         == 2
        assert str(again.stage_items[0].target_name) == 'lambda_entry.py'
        assert again.stage_items[1].is_tree   is True
