# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Events__Dashboard__Builder
# Pins the saved-objects ndjson shape: 7 objects (6 visualisations + 1
# dashboard), deterministic bytes, every visualization binds to the
# passed data view, every panel id appears in the dashboard refs.
# Includes the slice 1 lesson — string-typed terms-agg fields end with
# .keyword (numeric fields like time_taken_ms exempt).
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Builder import (
    CF__Events__Dashboard__Builder,
    DASHBOARD_DESCRIPTION,
)
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Ids import (
    DASHBOARD_ID, DASHBOARD_TITLE,
    VIS_ID__STATUS_OVER_TIME, VIS_ID__EDGE_RESULT, VIS_ID__TOP_URIS,
    VIS_ID__GEOGRAPHIC, VIS_ID__LATENCY_PERCENTILES, VIS_ID__BOT_VS_HUMAN,
)


def parse_ndjson(raw: bytes) -> list:
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


class test_CF__Events__Dashboard__Builder(TestCase):

    def test_ndjson_contains_seven_objects(self):
        raw = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        assert len(objects) == 7

    def test_visualizations_first_dashboard_last(self):
        raw     = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        for vis in objects[:6]:
            assert vis['type'] == 'visualization'
        assert objects[6]['type'] == 'dashboard'

    def test_visualization_ids_match_constants(self):
        raw     = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        ids = {o['id'] for o in objects[:6]}
        assert ids == {VIS_ID__STATUS_OVER_TIME, VIS_ID__EDGE_RESULT,
                       VIS_ID__TOP_URIS, VIS_ID__GEOGRAPHIC,
                       VIS_ID__LATENCY_PERCENTILES, VIS_ID__BOT_VS_HUMAN}

    def test_dashboard_id_and_title(self):
        raw       = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[6]
        assert dashboard['id']                       == DASHBOARD_ID
        assert dashboard['attributes']['title']      == DASHBOARD_TITLE
        assert dashboard['attributes']['description'] == DASHBOARD_DESCRIPTION

    def test_dashboard_references_all_six_visualizations(self):
        raw       = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[6]
        ref_ids = {ref['id'] for ref in dashboard['references']}
        assert ref_ids == {VIS_ID__STATUS_OVER_TIME, VIS_ID__EDGE_RESULT,
                           VIS_ID__TOP_URIS, VIS_ID__GEOGRAPHIC,
                           VIS_ID__LATENCY_PERCENTILES, VIS_ID__BOT_VS_HUMAN}

    def test_panels_layout_3x2_grid(self):                                          # 3 rows of 2 panels, each 24w x 12h on a 48-column canvas
        raw       = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        dashboard = parse_ndjson(raw)[6]
        panels    = json.loads(dashboard['attributes']['panelsJSON'])
        assert len(panels) == 6
        for p in panels:
            assert p['gridData']['w'] == 24
            assert p['gridData']['h'] == 12
        # Y-coordinates: 0, 0, 12, 12, 24, 24
        assert [p['gridData']['y'] for p in panels] == [0, 0, 12, 12, 24, 24]
        # X-coordinates alternate: 0, 24, 0, 24, 0, 24
        assert [p['gridData']['x'] for p in panels] == [0, 24, 0, 24, 0, 24]

    def test_every_visualization_binds_to_passed_data_view_id(self):
        raw     = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='my-test-view-id')
        objects = parse_ndjson(raw)
        for vis in objects[:6]:
            refs = vis['references']
            assert len(refs) == 1
            assert refs[0]['type'] == 'index-pattern'
            assert refs[0]['id']   == 'my-test-view-id'

    def test_deterministic_bytes_for_same_inputs(self):                             # Same inputs → byte-identical ndjson (idempotent re-import)
        b = CF__Events__Dashboard__Builder()
        out_a = b.build_ndjson(data_view_id='dv-fixture-uuid', time_field='timestamp')
        out_b = b.build_ndjson(data_view_id='dv-fixture-uuid', time_field='timestamp')
        assert out_a == out_b

    def test_string_terms_aggs_use_keyword_subfield(self):                          # Slice 1 regression — string-typed terms aggs MUST use .keyword. Numeric exempts.
        raw     = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        numeric_fields = {'time_taken_ms', 'sc_status', 'sc_bytes', 'ttfb_ms',
                          'origin_fbl_ms', 'origin_lbl_ms',
                          'delivery_year', 'delivery_month', 'delivery_day',
                          'delivery_hour', 'delivery_minute'}
        for vis in objects[:6]:
            vis_state = json.loads(vis['attributes']['visState'])
            for agg in vis_state.get('aggs', []):
                if agg.get('type') != 'terms':
                    continue
                field = agg.get('params', {}).get('field', '')
                if field in numeric_fields:
                    continue
                assert field.endswith('.keyword'), f'Terms agg on string field "{field}" must use .keyword (vis: {vis["id"]})'

    def test_percentiles_panel_uses_50_95_99(self):                                 # The latency-percentiles panel asks ES for these three points
        raw     = CF__Events__Dashboard__Builder().build_ndjson(data_view_id='dv-fixture-uuid')
        objects = parse_ndjson(raw)
        for vis in objects[:6]:
            if vis['id'] != VIS_ID__LATENCY_PERCENTILES:
                continue
            vis_state = json.loads(vis['attributes']['visState'])
            metric_aggs = [a for a in vis_state['aggs'] if a['type'] == 'percentiles']
            assert len(metric_aggs) == 1
            assert metric_aggs[0]['params']['percents'] == [50, 95, 99]
            assert metric_aggs[0]['params']['field']    == 'time_taken_ms'

    def test_helpers_expose_id_and_title(self):
        b = CF__Events__Dashboard__Builder()
        assert b.dashboard_id()    == DASHBOARD_ID
        assert b.dashboard_title() == DASHBOARD_TITLE
