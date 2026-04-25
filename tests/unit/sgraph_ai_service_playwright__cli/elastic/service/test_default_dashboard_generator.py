# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Default__Dashboard__Generator
# Sanity-checks the saved-objects ndjson produced for `sp el seed`'s default
# dashboard. We don't render against a live Kibana here — the import path is
# tested separately via Kibana__Saved_Objects__Client.import_objects with
# canned responses. These tests pin the *structure* the generator emits so a
# refactor doesn't silently drop a panel or a reference.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.service.Default__Dashboard__Generator import (
    Default__Dashboard__Generator,
    DASHBOARD_ID, DASHBOARD_TITLE,
    LENS_ID__LOG_LEVELS, LENS_ID__VOLUME_BY_LEVEL, LENS_ID__TOP_SERVICES, LENS_ID__AVG_DURATION,
)


class test_default_dashboard_generator(TestCase):

    def setUp(self):
        self.gen     = Default__Dashboard__Generator()
        self.bytes   = self.gen.build_ndjson(index='sg-synthetic', data_view_id='dv-uuid-123', time_field='timestamp')
        self.lines   = [line for line in self.bytes.decode('utf-8').split('\n') if line.strip()]
        self.objects = [json.loads(line) for line in self.lines]

    def test_emits_4_lens_and_1_dashboard_in_order(self):                            # 5 objects: 4 panels + 1 dashboard
        assert len(self.objects) == 5
        types_in_order = [o['type'] for o in self.objects]
        assert types_in_order == ['lens', 'lens', 'lens', 'lens', 'dashboard']

    def test_every_lens_references_the_supplied_data_view_id(self):                  # The whole point of generation: bake the data view id in
        lens_objects = [o for o in self.objects if o['type'] == 'lens']
        for lens in lens_objects:
            ids_in_refs = [r['id'] for r in lens.get('references', []) if r.get('type') == 'index-pattern']
            assert 'dv-uuid-123' in ids_in_refs, f'lens {lens["id"]} missing data view ref'

    def test_dashboard_references_all_four_lens_panels(self):
        dash = next(o for o in self.objects if o['type'] == 'dashboard')
        ref_ids = [r['id'] for r in dash['references'] if r['type'] == 'lens']
        assert sorted(ref_ids) == sorted([LENS_ID__LOG_LEVELS, LENS_ID__VOLUME_BY_LEVEL,
                                            LENS_ID__TOP_SERVICES, LENS_ID__AVG_DURATION])
        assert dash['id']                  == DASHBOARD_ID
        assert dash['attributes']['title'] == DASHBOARD_TITLE

    def test_panels_json_contains_one_entry_per_panel(self):                         # panelsJSON is JSON-string-encoded — parse and confirm 4 panels
        dash    = next(o for o in self.objects if o['type'] == 'dashboard')
        panels  = json.loads(dash['attributes']['panelsJSON'])
        assert len(panels) == 4
        ref_names = sorted(p['panelRefName'] for p in panels)
        assert ref_names == ['panel_lens-avg-duration', 'panel_lens-log-levels',
                              'panel_lens-top-services', 'panel_lens-volume-by-level']

    def test_time_field_threaded_into_date_histogram_columns(self):                  # When the user passes --time-field foo, every date_histogram should target foo
        custom = self.gen.build_ndjson(index='sg-synthetic', data_view_id='dv-uuid-123', time_field='@timestamp')
        for line in custom.decode('utf-8').split('\n'):
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj['type'] != 'lens':
                continue
            for layer in obj['attributes']['state']['datasourceStates']['formBased']['layers'].values():
                for col in layer['columns'].values():
                    if col.get('operationType') == 'date_histogram':
                        assert col['sourceField'] == '@timestamp'

    def test_ndjson_is_one_object_per_line_and_ends_with_newline(self):
        text = self.bytes.decode('utf-8')
        assert text.endswith('\n')
        for line in text.split('\n')[:-1]:                                           # Last split element is empty (trailing \n)
            json.loads(line)                                                         # raises if any line isn't valid JSON
