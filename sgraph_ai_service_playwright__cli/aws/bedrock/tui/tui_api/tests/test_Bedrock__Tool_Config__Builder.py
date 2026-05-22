# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api tests: Bedrock__Tool_Config__Builder
# Selected actions → a valid Bedrock toolConfig + a name→(slug,action) routing map. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider                  import S3__Tui_Api__Provider


def _actions():
    provider = S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory())
    return [('sg-aws.s3', action) for action in provider.manifest().actions]


def test_tool_names_are_valid_and_map_back():
    builder = Bedrock__Tool_Config__Builder()
    tool_config, name_map = builder.build(_actions())
    names = [tool['toolSpec']['name'] for tool in tool_config['tools']]
    assert all(re.match(r'^[a-zA-Z0-9_-]{1,64}$', name) for name in names)         # valid Bedrock tool names
    list_buckets_name = builder.tool_name('sg-aws.s3', 'list_buckets')
    assert name_map[list_buckets_name] == ('sg-aws.s3', 'list_buckets')


def test_inputschema_carries_real_json_schema():
    tool_config, _ = Bedrock__Tool_Config__Builder().build(_actions())
    list_objects = next(t for t in tool_config['tools'] if 'list_objects' in t['toolSpec']['name'])
    assert list_objects['toolSpec']['inputSchema']['json']['properties']['bucket']['type'] == 'string'
