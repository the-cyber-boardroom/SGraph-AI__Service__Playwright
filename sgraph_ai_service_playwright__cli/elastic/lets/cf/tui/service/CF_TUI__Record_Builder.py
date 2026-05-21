# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Record_Builder
# PURE: one CF real-time TSV line → Schema__CF_TUI__Record_View — every field walked
# from its RAW TSV column to the transformed/typed value, grouped RAW / DERIVED /
# LINEAGE / PIPELINE, with a `changed` flag where the transform altered the value.
# This is the "fields captured / transformed" view from the briefs. Reuses
# CF__Realtime__Log__Parser for the transform. No textual, no boto3 — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser, CF_REALTIME_COLUMN_COUNT
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Field_Row   import Schema__CF_TUI__Field_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Record_View import Schema__CF_TUI__Record_View


def sval(x) -> str:                                                                  # enum → its value; everything else → str()
    return x.value if hasattr(x, 'value') else str(x)


# (display name, TSV column index, transformed-value getter) for the 26 raw columns
RAW_SPECS = [
    ('timestamp',            0,  lambda r: str(r.timestamp)),
    ('time-taken',           1,  lambda r: f'{r.time_taken_ms}ms'),
    ('sc-status',            2,  lambda r: str(r.sc_status)),
    ('sc-bytes',             3,  lambda r: str(r.sc_bytes)),
    ('cs-method',            4,  lambda r: sval(r.cs_method)),
    ('cs-protocol',          5,  lambda r: sval(r.cs_protocol)),
    ('cs-host',              6,  lambda r: str(r.cs_host)),
    ('cs-uri-stem',          7,  lambda r: str(r.cs_uri_stem)),
    ('x-edge-location',      8,  lambda r: str(r.x_edge_location)),
    ('x-edge-request-id',    9,  lambda r: str(r.x_edge_request_id)),
    ('time-to-first-byte',   10, lambda r: f'{r.ttfb_ms}ms'),
    ('cs-protocol-version',  11, lambda r: str(r.cs_protocol_version)),
    ('cs-user-agent',        12, lambda r: str(r.cs_user_agent)),
    ('cs-referer',           13, lambda r: str(r.cs_referer)),
    ('x-edge-result-type',   14, lambda r: sval(r.x_edge_result_type)),
    ('ssl-protocol',         15, lambda r: sval(r.ssl_protocol)),
    ('ssl-cipher',           16, lambda r: str(r.ssl_cipher)),
    ('sc-content-type',      17, lambda r: str(r.sc_content_type)),
    ('sc-content-len',       18, lambda r: str(r.sc_content_len)),
    ('sc-range-start',       19, lambda r: str(r.sc_range_start)),
    ('sc-range-end',         20, lambda r: str(r.sc_range_end)),
    ('c-country',            21, lambda r: str(r.c_country)),
    ('cs-accept-encoding',   22, lambda r: str(r.cs_accept_encoding)),
    ('fle-status',           23, lambda r: str(r.fle_status)),
    ('origin-fbl',           24, lambda r: f'{r.origin_fbl_ms}ms'),
    ('origin-lbl',           25, lambda r: f'{r.origin_lbl_ms}ms'),
]


class CF_TUI__Record_Builder(Type_Safe):
    parser : CF__Realtime__Log__Parser

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    def build_from_text(self, tsv_text : str, key : str = '', line_index : int = 0, source_etag : str = '') -> Schema__CF_TUI__Record_View:
        valid = [ln for ln in tsv_text.split('\n')                                   # the lines the parser would accept (matches event indexing)
                 if ln.strip() and len(ln.rstrip('\r').split('\t')) == CF_REALTIME_COLUMN_COUNT]
        if line_index < len(valid):
            return self.build(valid[line_index], key=key, line_index=line_index, source_etag=source_etag)
        return Schema__CF_TUI__Record_View(key=key, line_index=line_index)

    def build(self, raw_line : str, key : str = '', line_index : int = 0, source_etag : str = '') -> Schema__CF_TUI__Record_View:
        self.setup()
        line   = raw_line.rstrip('\r')
        cols   = line.split('\t') if line.strip() else []
        doc_id = f'{source_etag}__{line_index}' if source_etag else f'line-{line_index}'
        view   = Schema__CF_TUI__Record_View(key=key, line_index=line_index, doc_id=doc_id, column_count=len(cols), raw_line=line)

        records, _ = self.parser.parse(line)
        if len(records) != 1:                                                        # wrong column count / unparseable → honest invalid view
            return view
        view.valid = True
        r = records[0]

        for name, idx, getter in RAW_SPECS:
            raw_val = cols[idx] if idx < len(cols) else ''
            value   = getter(r)
            view.fields.append(Schema__CF_TUI__Field_Row(group='RAW', name=name, raw=raw_val, value=value,
                                                         changed=(raw_val.strip() != value)))
        for name, value in (('sc_status_class', sval(r.sc_status_class)), ('cache_hit', str(r.cache_hit)),
                            ('bot_category', sval(r.bot_category)),       ('is_bot', str(r.is_bot))):
            view.fields.append(Schema__CF_TUI__Field_Row(group='DERIVED', name=name, value=value))
        for name, value in (('source_etag', str(r.source_etag) or source_etag), ('line_index', str(line_index)), ('doc_id', doc_id)):
            view.fields.append(Schema__CF_TUI__Field_Row(group='LINEAGE', name=name, value=value))
        for name, value in (('pipeline_run_id', str(r.pipeline_run_id)), ('loaded_at', str(r.loaded_at)), ('schema_version', str(r.schema_version))):
            view.fields.append(Schema__CF_TUI__Field_Row(group='PIPELINE', name=name, value=value))
        return view
