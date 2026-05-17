# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for extended Lambda__AWS__Client methods (v0.2.26)
# Covers: get_function_details, invoke, list_versions, list_aliases,
#         list_tags, tag_resource, untag_resource, update_function_configuration
# All tests use Lambda__AWS__Client__In_Memory. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__State          import Enum__Lambda__State
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name  import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import (
    Lambda__AWS__Client__In_Memory,
    Lambda__Deployer__In_Memory,
)

_NAME = 'ext-test-lambda'
_ARN  = f'arn:aws:lambda:eu-west-2:123456789012:function:{_NAME}'


def _client(store=None) -> Lambda__AWS__Client__In_Memory:
    return Lambda__AWS__Client__In_Memory(store=store or {})


def _deploy(client: Lambda__AWS__Client__In_Memory, name: str = _NAME) -> None:
    deployer = Lambda__Deployer__In_Memory(aws_client=client)
    req = Schema__Lambda__Deploy__Request(
        name        = Safe_Str__Lambda__Name(name),
        folder_path = '/tmp/fake',
        handler     = 'handler:handler',
        role_arn    = 'arn:aws:iam::123456789012:role/lambda-role',
    )
    deployer.deploy_from_folder(req)


# ═══════════════════════════════════════════════════════════════════════════════
class TestGetFunctionDetails:

    def test_returns_details_schema(self):
        client = _client()
        _deploy(client)
        details = client.get_function_details(_NAME)
        assert str(details.name) == _NAME
        assert details.state == Enum__Lambda__State.ACTIVE
        assert details.memory_size == 256          # default from deploy helper
        assert details.timeout     == 900

    def test_details_has_role_arn(self):
        client = _client()
        _deploy(client)
        details = client.get_function_details(_NAME)
        assert 'iam' in details.role_arn or 'role' in details.role_arn

    def test_details_has_architecture(self):
        client = _client()
        _deploy(client)
        details = client.get_function_details(_NAME)
        assert details.architecture == 'x86_64'


# ═══════════════════════════════════════════════════════════════════════════════
class TestInvoke:

    def test_sync_invoke_success(self):
        client = _client()
        _deploy(client)
        resp = client.invoke(_NAME, payload=b'{}')
        assert resp.success is True
        assert resp.status_code == 200
        assert 'ok' in resp.payload or resp.payload != ''

    def test_invoke_missing_function(self):
        client = _client()
        resp   = client.invoke('nonexistent', payload=b'{}')
        assert resp.success is False
        assert 'nonexistent' in resp.message


# ═══════════════════════════════════════════════════════════════════════════════
class TestListVersions:

    def test_returns_latest_version(self):
        client   = _client()
        _deploy(client)
        versions = client.list_versions(_NAME)
        assert len(versions) >= 1
        assert versions[0].version == '$LATEST'
        assert str(versions[0].name) == _NAME

    def test_missing_function_returns_empty(self):
        client   = _client()
        versions = client.list_versions('nonexistent')
        assert len(versions) == 0


# ═══════════════════════════════════════════════════════════════════════════════
class TestListAliases:

    def test_empty_by_default(self):
        client  = _client()
        _deploy(client)
        aliases = client.list_aliases(_NAME)
        assert len(aliases) == 0


# ═══════════════════════════════════════════════════════════════════════════════
class TestTags:

    def test_no_tags_initially(self):
        client = _client()
        _deploy(client)
        tags = client.list_tags(_ARN)
        assert tags == {}

    def test_set_and_list_tags(self):
        client = _client()
        _deploy(client)
        ok   = client.tag_resource(_ARN, {'Owner': 'dinis', 'Env': 'dev'})
        assert ok is True
        tags = client.list_tags(_ARN)
        assert tags.get('Owner') == 'dinis'
        assert tags.get('Env')   == 'dev'

    def test_untag_removes_key(self):
        client = _client()
        _deploy(client)
        client.tag_resource(_ARN, {'Owner': 'dinis', 'Env': 'dev'})
        ok   = client.untag_resource(_ARN, ['Env'])
        assert ok is True
        tags = client.list_tags(_ARN)
        assert 'Env' not in tags
        assert tags.get('Owner') == 'dinis'


# ═══════════════════════════════════════════════════════════════════════════════
class TestUpdateFunctionConfiguration:

    def test_update_memory(self):
        client = _client()
        _deploy(client)
        resp = client.update_function_configuration(_NAME, MemorySize=1024)
        assert resp.success is True
        fn   = client.get_function(_NAME)
        assert fn.memory_size == 1024

    def test_update_timeout(self):
        client = _client()
        _deploy(client)
        resp = client.update_function_configuration(_NAME, Timeout=30)
        assert resp.success is True
        fn   = client.get_function(_NAME)
        assert fn.timeout == 30

    def test_update_missing_function(self):
        client = _client()
        resp   = client.update_function_configuration('nonexistent', MemorySize=512)
        assert resp.success is False
