# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Schema__Builder
# Asserts Safe_Str params emit real JSON-Schema strings (the osbot emitter alone
# renders Safe_Str as {"type":"object"}; the builder corrects that). Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.schemas.Schema__S3__Params__List_Objects import Schema__S3__Params__List_Objects
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder            import Tui_Api__Schema__Builder


def test_input_schema_maps_safe_str_to_string():
    schema = Tui_Api__Schema__Builder().input_schema(Schema__S3__Params__List_Objects)
    props  = schema['properties']
    assert props['bucket']['type']    == 'string'                                 # Safe_Str__S3__Bucket → string (not 'object')
    assert props['prefix']['type']    == 'string'                                 # Safe_Str__S3__Prefix → string
    assert props['recursive']['type'] == 'boolean'                                # plain bool handled by the emitter
    assert 'bucket' in schema.get('required', [])                                 # no default → required
    assert 'prefix' not in schema.get('required', [])                             # has a default → optional


def test_string_field_carries_max_length_when_declared():
    schema = Tui_Api__Schema__Builder().input_schema(Schema__S3__Params__List_Objects)
    bucket = schema['properties']['bucket']
    assert bucket['type'] == 'string'
    assert isinstance(bucket.get('maxLength', 0), int)                            # maxLength surfaced from the Safe_Str when present
