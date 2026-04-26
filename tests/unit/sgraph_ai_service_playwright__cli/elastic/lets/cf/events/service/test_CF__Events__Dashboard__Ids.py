# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Events__Dashboard__Ids
# Pins the events dashboard saved-object id constants.  Phase 5 wiper
# imports these to delete; Phase 6 builder will import the same to create.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Ids import (
    DASHBOARD_ID, DASHBOARD_TITLE,
    VIS_ID__STATUS_OVER_TIME, VIS_ID__EDGE_RESULT, VIS_ID__TOP_URIS,
    VIS_ID__GEOGRAPHIC, VIS_ID__LATENCY_PERCENTILES, VIS_ID__BOT_VS_HUMAN,
    all_events_dashboard_refs,
)


class test_CF__Events__Dashboard__Ids(TestCase):

    def test_dashboard_constants(self):
        assert DASHBOARD_ID    == 'sg-cf-events-overview'
        assert DASHBOARD_TITLE == 'CloudFront Logs - Events Overview'

    def test_visualization_ids_share_prefix(self):                                  # All six panel ids follow "sg-cf-evt-vis-{slug}"
        for vis_id in (VIS_ID__STATUS_OVER_TIME, VIS_ID__EDGE_RESULT,
                        VIS_ID__TOP_URIS, VIS_ID__GEOGRAPHIC,
                        VIS_ID__LATENCY_PERCENTILES, VIS_ID__BOT_VS_HUMAN):
            assert vis_id.startswith('sg-cf-evt-vis-')

    def test_all_refs_returns_seven_tuples(self):                                   # 1 dashboard + 6 visualisations
        refs = all_events_dashboard_refs()
        assert len(refs) == 7
        types = sorted(t for t, _ in refs)
        assert types == ['dashboard'] + ['visualization'] * 6

    def test_dashboard_ref_first(self):                                             # Dashboard first so delete_saved_objects is ordered consistently
        assert all_events_dashboard_refs()[0] == ('dashboard', DASHBOARD_ID)

    def test_no_duplicate_ids(self):
        ids = [vid for _, vid in all_events_dashboard_refs()]
        assert len(ids) == len(set(ids))

    def test_distinct_from_inventory_ids(self):                                     # Events dashboard must not collide with the slice-1 inventory dashboard
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids import all_inventory_dashboard_refs
        events_ids    = {vid for _, vid in all_events_dashboard_refs()}
        inventory_ids = {vid for _, vid in all_inventory_dashboard_refs()}
        assert events_ids.isdisjoint(inventory_ids)
