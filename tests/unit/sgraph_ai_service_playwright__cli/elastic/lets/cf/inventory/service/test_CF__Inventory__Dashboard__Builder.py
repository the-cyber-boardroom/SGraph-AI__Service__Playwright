# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Inventory__Dashboard__Builder
# Pins the saved-objects ndjson shape: 6 objects (5 visualisations + 1
# dashboard), deterministic bytes for the same inputs, every visualization
# binds to the data view via the references array, every panel id is
# present in the dashboard's references.
#
# We deliberately do NOT pin the full visState JSON (those are 50+ lines
# of Kibana implementation detail) — instead we assert the shape: each
# object has the expected (id, type), the dashboard panel array has 5
# entries, and the panel layout is the documented 2x2 + full-width row.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Builder import (
    CF__Inventory__Dashboard__Builder,
    DASHBOARD_DESCRIPTION,
)
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids import (
    DASHBOARD_ID, DASHBOARD_TITLE,
    VIS_ID__COUNT_OVER_TIME, VIS_ID__BYTES_OVER_TIME,
    VIS_ID__SIZE_DISTRIBUTION, VIS_ID__STORAGE_CLASS_BREAKDOWN,
    VIS_ID__TOP_HOURLY_PARTITIONS,
)


def parse_ndjson(raw: bytes) -> list:                                               # ndjson → list of dicts
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


class test_CF__Inventory__Dashboard__Builder(TestCase):

    def test_ndjson_contains_six_objects(self):                                     # 5 visualizations + 1 dashboard
        raw = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        assert len(objects) == 6

    def test_visualizations_first_dashboard_last(self):                             # Import order matters — dashboard refs must resolve to already-imported visualizations
        raw     = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        for vis in objects[:5]:
            assert vis['type'] == 'visualization'
        assert objects[5]['type'] == 'dashboard'

    def test_visualization_ids_match_constants(self):                               # Each panel uses the deterministic id from CF__Inventory__Dashboard__Ids
        raw     = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        ids = {o['id'] for o in objects[:5]}
        assert ids == {VIS_ID__COUNT_OVER_TIME, VIS_ID__BYTES_OVER_TIME,
                       VIS_ID__SIZE_DISTRIBUTION, VIS_ID__STORAGE_CLASS_BREAKDOWN,
                       VIS_ID__TOP_HOURLY_PARTITIONS}

    def test_dashboard_id_and_title(self):
        raw       = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[5]
        assert dashboard['id']                       == DASHBOARD_ID
        assert dashboard['attributes']['title']      == DASHBOARD_TITLE
        assert dashboard['attributes']['description'] == DASHBOARD_DESCRIPTION

    def test_dashboard_references_all_five_visualizations(self):                    # Every panel id appears in dashboard.references
        raw       = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[5]
        ref_ids = {ref['id'] for ref in dashboard['references']}
        assert ref_ids == {VIS_ID__COUNT_OVER_TIME, VIS_ID__BYTES_OVER_TIME,
                           VIS_ID__SIZE_DISTRIBUTION, VIS_ID__STORAGE_CLASS_BREAKDOWN,
                           VIS_ID__TOP_HOURLY_PARTITIONS}

    def test_panels_layout_is_two_by_two_plus_full_width(self):                     # 2x2 grid (panels 1-4 at 24w x 12h) + full-width panel 5 (48w x 12h)
        raw       = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[5]
        panels    = json.loads(dashboard['attributes']['panelsJSON'])
        assert len(panels) == 5
        # First four panels: 24 wide x 12 tall in a 2x2 grid
        for p in panels[:4]:
            assert p['gridData']['w'] == 24
            assert p['gridData']['h'] == 12
        # Fifth panel: full width
        assert panels[4]['gridData']['w'] == 48
        assert panels[4]['gridData']['h'] == 12
        assert panels[4]['gridData']['x'] == 0
        assert panels[4]['gridData']['y'] == 24

    def test_every_visualization_binds_to_passed_data_view_id(self):                # The data_view_id arg propagates to every visualization's references entry
        raw     = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='my-test-view-id')
        objects = parse_ndjson(raw)
        for vis in objects[:5]:
            refs = vis['references']
            assert len(refs) == 1
            assert refs[0]['type'] == 'index-pattern'
            assert refs[0]['id']   == 'my-test-view-id'

    def test_deterministic_bytes_for_same_inputs(self):                             # Idempotent re-import requires byte-for-byte identical ndjson
        b = CF__Inventory__Dashboard__Builder()
        out_a = b.build_ndjson(data_view_id='dv-fixture-uuid', time_field='delivery_at')
        out_b = b.build_ndjson(data_view_id='dv-fixture-uuid', time_field='delivery_at')
        assert out_a == out_b

    def test_different_data_view_ids_produce_different_bytes(self):                 # Same builder but different data view → different output
        b = CF__Inventory__Dashboard__Builder()
        out_a = b.build_ndjson(data_view_id='view-a')
        out_b = b.build_ndjson(data_view_id='view-b')
        assert out_a != out_b

    def test_time_field_propagates_to_date_histogram_aggs(self):                    # The time_field arg flows into the visState aggs of the time-bucketed panels
        raw     = CF__Inventory__Dashboard__Builder().build_ndjson(data_view_id='dv', time_field='custom_time_field')
        objects = parse_ndjson(raw)
        # Panels 1 (count-over-time) and 2 (bytes-over-time) both use date_histogram on the time_field
        for vis in objects[:2]:
            vis_state = json.loads(vis['attributes']['visState'])
            date_aggs = [a for a in vis_state['aggs'] if a['type'] == 'date_histogram']
            assert len(date_aggs) == 1
            assert date_aggs[0]['params']['field'] == 'custom_time_field'

    def test_helpers_expose_id_and_title(self):                                     # Convenience accessors don't lie about the constants
        b = CF__Inventory__Dashboard__Builder()
        assert b.dashboard_id()    == DASHBOARD_ID
        assert b.dashboard_title() == DASHBOARD_TITLE
