# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Image__Stage__Item
# Pure-data round-trip + default values.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item     import Schema__Image__Stage__Item


class test_Schema__Image__Stage__Item(TestCase):

    def test__defaults(self):
        item = Schema__Image__Stage__Item()
        assert str(item.source_path)         == ''
        assert str(item.target_name)         == ''
        assert item.is_tree                  is False
        assert list(item.extra_ignore_names) == []

    def test__round_trip_via_json(self):
        item = Schema__Image__Stage__Item(source_path='/abs/src/pkg', target_name='pkg', is_tree=True,
                                          extra_ignore_names=['images', 'docs'])
        again = Schema__Image__Stage__Item.from_json(item.json())
        assert str(again.source_path)         == '/abs/src/pkg'
        assert str(again.target_name)         == 'pkg'
        assert again.is_tree                  is True
        assert list(again.extra_ignore_names) == ['images', 'docs']

    def test__file_item_has_no_extra_ignores_used(self):                            # extra_ignore_names is meaningful only for trees; defensive: no exception when set on a file item
        item = Schema__Image__Stage__Item(source_path='/abs/lambda_entry.py', target_name='lambda_entry.py',
                                          is_tree=False, extra_ignore_names=['ignored'])
        assert item.is_tree is False                                                # Service applies extra_ignore_names only on the copytree branch
