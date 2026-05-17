# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__AWS__Client
# All tests use Lambda__AWS__Client__In_Memory. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__State          import Enum__Lambda__State
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Url__Auth_Type import Enum__Lambda__Url__Auth_Type
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import Lambda__AWS__Client__In_Memory, Lambda__Deployer__In_Memory
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name  import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request


_NAME = 'echo-lambda'


def _client(store=None, url_store=None) -> Lambda__AWS__Client__In_Memory:
    return Lambda__AWS__Client__In_Memory(store=store or {}, url_store=url_store or {})


def _deploy(client: Lambda__AWS__Client__In_Memory, name: str = _NAME) -> None:
    deployer = Lambda__Deployer__In_Memory(aws_client=client)
    req = Schema__Lambda__Deploy__Request(
        name        = Safe_Str__Lambda__Name(name),
        folder_path = '/tmp/fake',
        handler     = 'handler:handler',
        role_arn    = 'arn:aws:iam::123456789012:role/lambda-role',
    )
    deployer.deploy_from_folder(req)


class TestListFunctions:
    def test_empty(self):
        client = _client()
        result = client.list_functions()
        assert len(result) == 0

    def test_after_deploy_returns_one(self):
        client = _client()
        _deploy(client)
        result = client.list_functions()
        assert len(result) == 1
        assert str(result[0].name) == _NAME

    def test_two_deploys_returns_two(self):
        client = _client()
        _deploy(client, 'fn-a')
        _deploy(client, 'fn-b')
        result = client.list_functions()
        assert len(result) == 2


class TestGetFunction:
    def test_get_existing(self):
        client = _client()
        _deploy(client)
        fn = client.get_function(_NAME)
        assert str(fn.name) == _NAME
        assert fn.state == Enum__Lambda__State.ACTIVE

    def test_get_missing_raises(self):
        client = _client()
        try:
            client.get_function('nonexistent')
            assert False, 'expected exception'
        except Exception as e:
            assert 'nonexistent' in str(e)


class TestExists:
    def test_exists_true(self):
        client = _client()
        _deploy(client)
        assert client.exists(_NAME) is True

    def test_exists_false(self):
        assert _client().exists('missing') is False


class TestDeleteFunction:
    def test_delete_existing(self):
        client = _client()
        _deploy(client)
        resp = client.delete_function(_NAME)
        assert resp.success is True
        assert client.exists(_NAME) is False

    def test_delete_missing_fails(self):
        client = _client()
        resp   = client.delete_function('missing')
        assert resp.success is False


class TestFunctionUrl:
    def test_get_url_when_none_exists(self):
        client = _client()
        info   = client.get_function_url(_NAME)
        assert info.exists is False

    def test_create_url_none_auth(self):
        client = _client()
        _deploy(client)
        info   = client.create_function_url(_NAME, auth_type=Enum__Lambda__Url__Auth_Type.NONE)
        assert info.exists is True
        assert 'lambda-url' in str(info.function_url)
        assert info.auth_type == Enum__Lambda__Url__Auth_Type.NONE

    def test_get_url_after_create(self):
        client = _client()
        _deploy(client)
        client.create_function_url(_NAME)
        info = client.get_function_url(_NAME)
        assert info.exists is True

    def test_delete_url(self):
        client = _client()
        _deploy(client)
        client.create_function_url(_NAME)
        resp = client.delete_function_url(_NAME)
        assert resp.success is True
        assert client.get_function_url(_NAME).exists is False

    def test_delete_url_missing(self):
        client = _client()
        resp   = client.delete_function_url('missing')
        assert resp.success is False


class TestDeployer:
    def test_deploy_creates_function(self):
        client   = _client()
        deployer = Lambda__Deployer__In_Memory(aws_client=client)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(_NAME),
            folder_path = '/tmp/fake',
            handler     = 'handler:handler',
            role_arn    = 'arn:aws:iam::123456789012:role/lambda-role',
        )
        resp = deployer.deploy_from_folder(req)
        assert resp.success  is True
        assert resp.created  is True
        assert resp.message  == 'created'
        assert client.exists(_NAME) is True

    def test_deploy_update_existing(self):
        client = _client()
        _deploy(client)
        deployer = Lambda__Deployer__In_Memory(aws_client=client)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(_NAME),
            folder_path = '/tmp/fake',
            handler     = 'handler_v2:handler',
            role_arn    = 'arn:aws:iam::123456789012:role/lambda-role',
        )
        resp = deployer.deploy_from_folder(req)
        assert resp.success is True
        assert resp.created is False
        assert resp.message == 'updated'
