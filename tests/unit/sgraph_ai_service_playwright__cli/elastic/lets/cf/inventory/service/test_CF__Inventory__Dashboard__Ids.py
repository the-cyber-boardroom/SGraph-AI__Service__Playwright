# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Inventory__Dashboard__Ids
# Pins the dashboard saved-object id constants and the helper function the
# wiper consumes. Both the wiper (Phase 4) and the dashboard builder
# (Phase 5) import from this module — they MUST agree on these ids.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids import (
    DASHBOARD_ID, DASHBOARD_TITLE,
    VIS_ID__COUNT_OVER_TIME, VIS_ID__BYTES_OVER_TIME,
    VIS_ID__SIZE_DISTRIBUTION, VIS_ID__STORAGE_CLASS_BREAKDOWN,
    VIS_ID__TOP_HOURLY_PARTITIONS,
    all_inventory_dashboard_refs,
)


class test_CF__Inventory__Dashboard__Ids(TestCase):

    def test_dashboard_constants(self):
        assert DASHBOARD_ID    == 'sg-cf-inventory-overview'
        assert DASHBOARD_TITLE == 'CloudFront Logs - Inventory Overview'

    def test_visualization_ids_share_prefix(self):                                  # All five panel ids follow "sg-cf-inv-vis-{slug}" — assert the convention
        for vis_id in (VIS_ID__COUNT_OVER_TIME, VIS_ID__BYTES_OVER_TIME,
                        VIS_ID__SIZE_DISTRIBUTION, VIS_ID__STORAGE_CLASS_BREAKDOWN,
                        VIS_ID__TOP_HOURLY_PARTITIONS):
            assert vis_id.startswith('sg-cf-inv-vis-')

    def test_all_refs_returns_six_tuples(self):                                     # 1 dashboard + 5 visualisations
        refs = all_inventory_dashboard_refs()
        assert len(refs) == 6
        types = sorted(t for t, _ in refs)
        assert types == ['dashboard', 'visualization', 'visualization',
                         'visualization', 'visualization', 'visualization']

    def test_dashboard_ref_first(self):                                             # The dashboard must come first so delete_saved_objects can be ordered
        assert all_inventory_dashboard_refs()[0] == ('dashboard', DASHBOARD_ID)

    def test_no_duplicate_ids(self):                                                # Catch copy-paste bugs at the constant level
        ids = [vid for _, vid in all_inventory_dashboard_refs()]
        assert len(ids) == len(set(ids))
