# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish tests — Vault_Publish__Service.bootstrap()
# End-to-end bootstrap test using in-memory CF + Lambda fakes.
# No mocks, no patches, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client       import CloudFront__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer         import Lambda__Deployer

from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Bootstrap__Request  import (
    Schema__Vault_Publish__Bootstrap__Request, DEFAULT_CERT_ARN, DEFAULT_ZONE)
from sg_compute_specs.vault_publish.service.Vault_Publish__Service                  import (
    Vault_Publish__Service, WAKER_LAMBDA_NAME)


# ── In-memory fakes ───────────────────────────────────────────────────────────

class _Fake_CF_Client:
    _counter = 0

    def __init__(self, store: dict):
        self._store   = store
        self._configs = {}

    def _etag(self, dist_id): return f'ETAG-{dist_id}'

    def list_distributions(self, **_):
        return {'DistributionList': {'Items': list(self._store.values()), 'IsTruncated': False}}

    def get_distribution(self, Id):
        dist = self._store.get(Id)
        if not dist:
            raise Exception(f'No such distribution: {Id}')
        return {'Distribution': {**dist, 'DistributionConfig': self._configs.get(Id, {})},
                'ETag': self._etag(Id)}

    def get_distribution_config(self, Id):
        return {'DistributionConfig': self._configs.get(Id, {'Enabled': True}),
                'ETag': self._etag(Id)}

    def create_distribution(self, DistributionConfig: dict):
        _Fake_CF_Client._counter += 1
        dist_id = f'ECFTEST{_Fake_CF_Client._counter:06d}'
        domain  = f'{dist_id.lower()}.cloudfront.net'
        entry   = {
            'Id'              : dist_id,
            'DomainName'      : domain,
            'Status'          : 'InProgress',
            'Comment'         : DistributionConfig.get('Comment', ''),
            'Enabled'         : DistributionConfig.get('Enabled', True),
            'ViewerCertificate': DistributionConfig.get('ViewerCertificate', {}),
            'PriceClass'      : DistributionConfig.get('PriceClass', 'PriceClass_All'),
            'Aliases'         : DistributionConfig.get('Aliases', {'Quantity': 0, 'Items': []}),
            'LastModifiedTime': '',
        }
        self._store[dist_id]   = entry
        self._configs[dist_id] = DistributionConfig
        return {'Distribution': entry, 'ETag': self._etag(dist_id)}

    def update_distribution(self, Id, DistributionConfig, IfMatch): pass
    def delete_distribution(self, Id, IfMatch): pass


class _CF__In_Memory(CloudFront__AWS__Client):
    def __init__(self):
        super().__init__()
        self._store      = {}
        self._fake_client = _Fake_CF_Client(self._store)

    def client(self):
        return self._fake_client


class _Fake_Lambda_Client:
    def __init__(self, store: dict, url_store: dict):
        self._store     = store
        self._url_store = url_store

    def get_paginator(self, method): return _Fake_Paginator(self)

    def get_function(self, FunctionName):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')
        return {'Configuration': self._store[FunctionName]}

    def create_function(self, FunctionName, Runtime, Role, Handler,
                        Code, Timeout=60, MemorySize=128, Description='', **_):
        arn = f'arn:aws:lambda:eu-west-2:123456789012:function:{FunctionName}'
        self._store[FunctionName] = {
            'FunctionName': FunctionName, 'FunctionArn': arn,
            'Runtime': Runtime, 'Handler': Handler,
            'MemorySize': MemorySize, 'Timeout': Timeout,
            'Description': Description, 'State': 'Active', 'LastModified': '',
        }
        return self._store[FunctionName]

    def update_function_code(self, FunctionName, ZipFile, **_): pass
    def update_function_configuration(self, FunctionName, **_): pass
    def delete_function(self, FunctionName, **_): del self._store[FunctionName]

    def get_function_url_config(self, FunctionName, **_):
        if FunctionName not in self._url_store:
            raise Exception(f'No URL: {FunctionName}')
        return self._url_store[FunctionName]

    def create_function_url_config(self, FunctionName, AuthType, **_):
        url = f'https://fakewaker.lambda-url.eu-west-2.on.aws/'
        self._url_store[FunctionName] = {'FunctionUrl': url, 'AuthType': AuthType}
        return self._url_store[FunctionName]

    def add_permission(self, **_): pass
    def delete_function_url_config(self, FunctionName, **_): del self._url_store[FunctionName]


class _Fake_Paginator:
    def __init__(self, client): self._client = client
    def paginate(self, **_):   yield {'Functions': list(self._client._store.values())}


class _Lambda__Client__In_Memory(Lambda__AWS__Client):
    def __init__(self):
        super().__init__()
        self._fn_store  = {}
        self._url_store = {}
        self._fake      = _Fake_Lambda_Client(self._fn_store, self._url_store)

    def client(self): return self._fake


class _Lambda__Deployer__In_Memory(Lambda__Deployer):
    def __init__(self, lc: _Lambda__Client__In_Memory):
        super().__init__()
        self._lc = lc

    def client(self):              return self._lc._fake
    def _zip_folder(self, path):   return b'FAKE_ZIP'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc_with_fakes():
    cf     = _CF__In_Memory()
    lc     = _Lambda__Client__In_Memory()
    dep    = _Lambda__Deployer__In_Memory(lc)
    svc    = Vault_Publish__Service(
        _cf_client_factory     = lambda: cf,
        _lambda_client_factory = lambda: lc,
        _deployer_factory      = lambda: dep,
    )
    return svc, cf, lc, dep


def _req(**kw):
    return Schema__Vault_Publish__Bootstrap__Request(**kw)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestBootstrapResponse:
    def test_bootstrap_returns_response(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp is not None

    def test_bootstrap_success_flag(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.created is True

    def test_bootstrap_message_is_bootstrapped(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.message == 'bootstrapped'

    def test_bootstrap_lambda_name(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.lambda_name == WAKER_LAMBDA_NAME

    def test_bootstrap_zone_echoed(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req(zone='example.sg-labs.app'))
        assert resp.zone == 'example.sg-labs.app'

    def test_bootstrap_default_zone(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.zone == DEFAULT_ZONE

    def test_bootstrap_waker_url_populated(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.waker_url.startswith('https://')

    def test_bootstrap_distribution_id_populated(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.distribution_id != ''

    def test_bootstrap_domain_name_populated(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert 'cloudfront.net' in resp.domain_name

    def test_bootstrap_elapsed_ms_non_negative(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap(_req())
        assert resp.elapsed_ms >= 0


class TestBootstrapLambdaSideEffects:
    def test_lambda_function_created(self):
        svc, _, lc, _ = _svc_with_fakes()
        svc.bootstrap(_req())
        assert WAKER_LAMBDA_NAME in lc._fn_store

    def test_lambda_function_url_created(self):
        svc, _, lc, _ = _svc_with_fakes()
        svc.bootstrap(_req())
        assert WAKER_LAMBDA_NAME in lc._url_store

    def test_lambda_function_url_is_https(self):
        svc, _, lc, _ = _svc_with_fakes()
        svc.bootstrap(_req())
        url = lc._url_store[WAKER_LAMBDA_NAME]['FunctionUrl']
        assert url.startswith('https://')

    def test_lambda_handler_set(self):
        svc, _, lc, _ = _svc_with_fakes()
        svc.bootstrap(_req())
        assert lc._fn_store[WAKER_LAMBDA_NAME]['Handler'] == 'lambda_entry.run'


class TestBootstrapCFSideEffects:
    def test_cf_distribution_created(self):
        svc, cf, *_ = _svc_with_fakes()
        svc.bootstrap(_req())
        assert len(cf._store) == 1

    def test_cf_distribution_comment_contains_zone(self):
        svc, cf, *_ = _svc_with_fakes()
        svc.bootstrap(_req(zone='aws.sg-labs.app'))
        dist_id = list(cf._store)[0]
        assert 'aws.sg-labs.app' in cf._store[dist_id]['Comment']

    def test_cf_origin_uses_lambda_domain(self):
        svc, cf, lc, _ = _svc_with_fakes()
        svc.bootstrap(_req())
        dist_id = list(cf._store)[0]
        config  = cf._fake_client._configs[dist_id]
        origins = config.get('Origins', {}).get('Items', [])
        assert len(origins) == 1
        lambda_domain = lc._url_store[WAKER_LAMBDA_NAME]['FunctionUrl'].removeprefix('https://').rstrip('/')
        assert origins[0]['DomainName'] == lambda_domain

    def test_cf_aliases_contain_wildcard(self):
        svc, cf, *_ = _svc_with_fakes()
        svc.bootstrap(_req(zone='aws.sg-labs.app'))
        dist_id = list(cf._store)[0]
        config  = cf._fake_client._configs[dist_id]
        aliases = config.get('Aliases', {}).get('Items', [])
        assert '*.aws.sg-labs.app' in aliases


class TestBootstrapNoSideEffectsOnFailure:
    def test_deploy_failure_returns_error_response(self):
        class _Bad_Deployer(Lambda__Deployer):
            def deploy_from_folder(self, req):
                from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
                from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Response import Schema__Lambda__Deploy__Response
                return Schema__Lambda__Deploy__Response(
                    name=Safe_Str__Lambda__Name(str(req.name)), success=False, message='boom')

        cf  = _CF__In_Memory()
        lc  = _Lambda__Client__In_Memory()
        svc = Vault_Publish__Service(
            _cf_client_factory     = lambda: cf,
            _lambda_client_factory = lambda: lc,
            _deployer_factory      = lambda: _Bad_Deployer(),
        )
        resp = svc.bootstrap(_req())
        assert resp.created is False
        assert 'boom' in resp.message

    def test_deploy_failure_no_cf_distribution_created(self):
        class _Bad_Deployer(Lambda__Deployer):
            def deploy_from_folder(self, req):
                from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
                from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Response import Schema__Lambda__Deploy__Response
                return Schema__Lambda__Deploy__Response(
                    name=Safe_Str__Lambda__Name(str(req.name)), success=False, message='boom')

        cf  = _CF__In_Memory()
        lc  = _Lambda__Client__In_Memory()
        svc = Vault_Publish__Service(
            _cf_client_factory     = lambda: cf,
            _lambda_client_factory = lambda: lc,
            _deployer_factory      = lambda: _Bad_Deployer(),
        )
        svc.bootstrap(_req())
        assert len(cf._store) == 0


class TestBootstrapRequestDefaults:
    def test_default_cert_arn(self):
        req = Schema__Vault_Publish__Bootstrap__Request()
        assert req.cert_arn == DEFAULT_CERT_ARN

    def test_default_zone(self):
        req = Schema__Vault_Publish__Bootstrap__Request()
        assert req.zone == DEFAULT_ZONE

    def test_default_role_arn_empty(self):
        req = Schema__Vault_Publish__Bootstrap__Request()
        assert req.role_arn == ''

    def test_no_arg_bootstrap_uses_defaults(self):
        svc, *_ = _svc_with_fakes()
        resp = svc.bootstrap()
        assert resp.zone == DEFAULT_ZONE
        assert resp.created is True
