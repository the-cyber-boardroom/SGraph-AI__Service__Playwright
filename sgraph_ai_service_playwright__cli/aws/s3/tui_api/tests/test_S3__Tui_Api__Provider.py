# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/s3/tui_api tests: S3__Tui_Api__Provider
# Drives the provider over the in-memory S3 client (no mocks, no AWS). Asserts the
# manifest carries real JSON Schema and that dispatch returns structured results. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider import S3__Tui_Api__Provider


def _provider():
    client = (S3__AWS__Client__In_Memory().add_bucket('demo-bucket')
                                          .add_object('demo-bucket', 'top.txt',    b'hello')
                                          .add_object('demo-bucket', 'logs/a.txt', b'xx'))
    return S3__Tui_Api__Provider(client=client)


def test_manifest_actions_and_real_schema():
    manifest = _provider().manifest()
    names    = [str(a.name) for a in manifest.actions]
    assert names == ['list_buckets', 'list_objects', 'head_object']
    list_objects = next(a for a in manifest.actions if str(a.name) == 'list_objects')
    assert list_objects.input_schema['properties']['bucket']['type'] == 'string'
    assert str(list_objects.tier) == 'read_only'


def test_dispatch_list_buckets():
    out = _provider().dispatch('list_buckets', {}).json()
    assert out['ok'] is True
    assert 'demo-bucket' in [b['name'] for b in out['data']['result']]


def test_dispatch_list_objects_recursive():
    out = _provider().dispatch('list_objects', {'bucket': 'demo-bucket', 'recursive': True}).json()
    assert out['ok'] is True
    keys = [o['key'] for o in out['data']['result']['objects']]
    assert 'top.txt' in keys and 'logs/a.txt' in keys


def test_dispatch_head_object():
    out = _provider().dispatch('head_object', {'bucket': 'demo-bucket', 'key': 'top.txt'}).json()
    assert out['ok'] is True
    assert out['data']['result']['size'] == 5


def test_dispatch_unknown_action():
    result = _provider().dispatch('bogus', {})
    assert result.ok is False
    assert 'unknown action' in result.error


def test_skills_present_and_name_actions():
    skills = _provider().skills()
    assert set(skills) == {'human', 'api', 'driver'}
    assert 'list_objects' in skills['api']
