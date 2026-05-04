# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Default__Dashboard__Generator
# Sanity-checks the saved-objects ndjson produced for `sp el seed`'s default
# dashboard. We don't render against a live Kibana here — these tests pin the
# *structure* the generator emits so a refactor doesn't silently drop a panel
# or break a reference.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.service.Default__Dashboard__Generator import (
    Default__Dashboard__Generator,
    DASHBOARD_ID, DASHBOARD_TITLE, DATA_VIEW_REF_NAME,
    VIS_ID__LOG_LEVELS, VIS_ID__VOLUME_BY_LEVEL, VIS_ID__TOP_SERVICES, VIS_ID__AVG_DURATION,
)


class test_default_dashboard_generator(TestCase):

    def setUp(self):
        self.gen     = Default__Dashboard__Generator()
        self.bytes   = self.gen.build_ndjson(index='sg-synthetic', data_view_id='dv-uuid-123', time_field='timestamp')
        self.lines   = [line for line in self.bytes.decode('utf-8').split('\n') if line.strip()]
        self.objects = [json.loads(line) for line in self.lines]

    def test_emits_4_visualizations_and_1_dashboard_in_order(self):
        assert len(self.objects) == 5
        types_in_order = [o['type'] for o in self.objects]
        assert types_in_order == ['visualization', 'visualization', 'visualization', 'visualization', 'dashboard']

    def test_every_visualization_references_the_supplied_data_view_id(self):
        viz_objects = [o for o in self.objects if o['type'] == 'visualization']
        for viz in viz_objects:
            ids_in_refs = [r['id'] for r in viz.get('references', []) if r.get('type') == 'index-pattern']
            assert 'dv-uuid-123' in ids_in_refs, f'viz {viz["id"]} missing data view ref'

    def test_data_view_reference_uses_index_ref_name_convention(self):              # Vis Editor encodes the data view as kibanaSavedObjectMeta.searchSourceJSON.index, referenced by name from the references array
        viz = next(o for o in self.objects if o['type'] == 'visualization')
        ref_names = [r['name'] for r in viz['references']]
        assert DATA_VIEW_REF_NAME in ref_names
        # And the searchSourceJSON references it by the same name
        search_source = json.loads(viz['attributes']['kibanaSavedObjectMeta']['searchSourceJSON'])
        assert search_source['indexRefName'] == DATA_VIEW_REF_NAME

    def test_visstate_is_a_json_encoded_string(self):                                # Kibana convention: visState is a string, not a nested object
        viz = next(o for o in self.objects if o['type'] == 'visualization')
        assert isinstance(viz['attributes']['visState'], str)
        parsed = json.loads(viz['attributes']['visState'])
        assert parsed.get('type') in ('pie', 'histogram', 'horizontal_bar', 'line')

    def test_pie_uses_terms_on_level_keyword(self):
        pie = next(o for o in self.objects if o['id'] == VIS_ID__LOG_LEVELS)
        state = json.loads(pie['attributes']['visState'])
        assert state['type'] == 'pie'
        terms_agg = next(a for a in state['aggs'] if a['type'] == 'terms')
        assert terms_agg['params']['field'] == 'level.keyword'

    def test_volume_chart_splits_by_level_over_time(self):
        vol   = next(o for o in self.objects if o['id'] == VIS_ID__VOLUME_BY_LEVEL)
        state = json.loads(vol['attributes']['visState'])
        agg_types = [a['type'] for a in state['aggs']]
        assert 'count'           in agg_types
        assert 'date_histogram'  in agg_types
        assert 'terms'           in agg_types
        date_agg  = next(a for a in state['aggs'] if a['type'] == 'date_histogram')
        terms_agg = next(a for a in state['aggs'] if a['type'] == 'terms')
        assert date_agg ['params']['field'] == 'timestamp'
        assert terms_agg['params']['field'] == 'level.keyword'

    def test_avg_duration_uses_avg_metric_on_duration_ms(self):
        avg   = next(o for o in self.objects if o['id'] == VIS_ID__AVG_DURATION)
        state = json.loads(avg['attributes']['visState'])
        avg_agg = next(a for a in state['aggs'] if a['type'] == 'avg')
        assert avg_agg['params']['field'] == 'duration_ms'

    def test_dashboard_references_all_four_panels(self):
        dash    = next(o for o in self.objects if o['type'] == 'dashboard')
        ref_ids = sorted(r['id'] for r in dash['references'] if r['type'] == 'visualization')
        assert ref_ids == sorted([VIS_ID__LOG_LEVELS, VIS_ID__VOLUME_BY_LEVEL,
                                    VIS_ID__TOP_SERVICES, VIS_ID__AVG_DURATION])
        assert dash['id']                  == DASHBOARD_ID
        assert dash['attributes']['title'] == DASHBOARD_TITLE

    def test_panels_json_uses_panel_underscore_panelindex_convention(self):          # panelRefName must match a name in the dashboard references array — Kibana resolves the visualization id by that lookup
        dash    = next(o for o in self.objects if o['type'] == 'dashboard')
        panels  = json.loads(dash['attributes']['panelsJSON'])
        assert len(panels) == 4
        # Every panel's panelRefName must exist in the dashboard's references
        ref_names = {r['name'] for r in dash['references']}
        for p in panels:
            assert p['panelRefName'] in ref_names, f'panel {p["panelIndex"]} ref name {p["panelRefName"]} not in references'
            assert p['panelRefName'] == f'panel_{p["panelIndex"]}'                   # Convention check

    def test_time_field_threaded_into_date_histogram_aggs(self):
        custom = self.gen.build_ndjson(index='sg-synthetic', data_view_id='dv-uuid-123', time_field='@timestamp')
        for line in custom.decode('utf-8').split('\n'):
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj['type'] != 'visualization':
                continue
            state = json.loads(obj['attributes']['visState'])
            for agg in state['aggs']:
                if agg['type'] == 'date_histogram':
                    assert agg['params']['field'] == '@timestamp'

    def test_ndjson_is_one_object_per_line_and_ends_with_newline(self):
        text = self.bytes.decode('utf-8')
        assert text.endswith('\n')
        for line in text.split('\n')[:-1]:
            json.loads(line)
