# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__AWS__Client__In_Memory
# In-memory fake boto3 Lambda client for unit tests.
# No mocks. No patches. Dict-backed dispatch.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client import Lambda__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer    import Lambda__Deployer


class _Fake_Lambda_Client:
    """Minimal boto3-alike Lambda + Paginator client backed by a shared dict store."""

    def __init__(self, store: dict, url_store: dict):
        self._store      = store
        self._url_store  = url_store
        self._tags_store = {}                                                          # arn -> tag dict
        self._invoke_log = []                                                          # list of (name, payload) pairs

    # ── paginator ─────────────────────────────────────────────────────────────

    def get_paginator(self, method: str):
        return _Fake_Paginator(self, method)

    # ── function CRUD ─────────────────────────────────────────────────────────

    def get_function(self, FunctionName: str):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')
        return {'Configuration': self._store[FunctionName]}

    def create_function(self, FunctionName: str, Runtime: str, Role: str,
                        Handler: str, Code: dict, Timeout: int = 60,
                        MemorySize: int = 128, Description: str = '', **_):
        arn = f'arn:aws:lambda:eu-west-2:123456789012:function:{FunctionName}'
        self._store[FunctionName] = {
            'FunctionName': FunctionName,
            'FunctionArn' : arn,
            'Runtime'     : Runtime,
            'Handler'     : Handler,
            'MemorySize'  : MemorySize,
            'Timeout'     : Timeout,
            'Description' : Description,
            'State'       : 'Active',
            'LastModified': '',
            'Role'        : Role,
            'CodeSize'    : 0,
            'Architectures': ['x86_64'],
            'TracingConfig': {'Mode': 'PassThrough'},
            'EphemeralStorage': {'Size': 512},
        }
        return self._store[FunctionName]

    def update_function_code(self, FunctionName: str, ZipFile: bytes, **_):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')

    def update_function_configuration(self, FunctionName: str, **kwargs):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')
        mapping = {                                                                    # allow both old positional and new kwarg forms
            'Handler'    : 'Handler',
            'Runtime'    : 'Runtime',
            'Timeout'    : 'Timeout',
            'MemorySize' : 'MemorySize',
            'Description': 'Description',
            'Environment': 'Environment',
        }
        for key in mapping:
            if key in kwargs:
                self._store[FunctionName][key] = kwargs[key]

    def delete_function(self, FunctionName: str, **_):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')
        del self._store[FunctionName]

    # ── invoke ────────────────────────────────────────────────────────────────

    def invoke(self, FunctionName: str, InvocationType: str = 'RequestResponse',
               Payload: bytes = b'{}', LogType: str = 'None', **_):
        if FunctionName not in self._store:
            raise Exception(f'Function not found: {FunctionName}')
        self._invoke_log.append((FunctionName, Payload))
        import io
        resp = {
            'StatusCode'   : 200,
            'Payload'      : io.BytesIO(b'{"result": "ok"}'),
            'FunctionError': '',
            'LogResult'    : '',
        }
        return resp

    # ── tags ──────────────────────────────────────────────────────────────────

    def list_tags(self, Resource: str, **_):
        return {'Tags': dict(self._tags_store.get(Resource, {}))}

    def tag_resource(self, Resource: str, Tags: dict, **_):
        if Resource not in self._tags_store:
            self._tags_store[Resource] = {}
        self._tags_store[Resource].update(Tags)

    def untag_resource(self, Resource: str, TagKeys: list, **_):
        for k in TagKeys:
            self._tags_store.get(Resource, {}).pop(k, None)

    # ── URL management ────────────────────────────────────────────────────────

    def get_function_url_config(self, FunctionName: str, **_):
        if FunctionName not in self._url_store:
            raise Exception(f'No URL for function: {FunctionName}')
        return self._url_store[FunctionName]

    def create_function_url_config(self, FunctionName: str, AuthType: str, **_):
        url = f'https://fakeid.lambda-url.eu-west-2.on.aws/'
        self._url_store[FunctionName] = {'FunctionUrl': url, 'AuthType': AuthType}
        return self._url_store[FunctionName]

    def add_permission(self, **_):
        pass

    def delete_function_url_config(self, FunctionName: str, **_):
        if FunctionName not in self._url_store:
            raise Exception(f'No URL for function: {FunctionName}')
        del self._url_store[FunctionName]


class _Fake_Paginator:
    def __init__(self, client: _Fake_Lambda_Client, method: str):
        self._client = client
        self._method = method

    def paginate(self, FunctionName: str = None, **_):
        if self._method == 'list_functions':
            yield {'Functions': list(self._client._store.values())}
        elif self._method == 'list_versions_by_function':
            cfg = self._client._store.get(FunctionName, {})
            if cfg:
                yield {'Versions': [{
                    'FunctionName': FunctionName,
                    'Version'     : '$LATEST',
                    'Description' : '',
                    'LastModified': cfg.get('LastModified', ''),
                    'CodeSize'    : cfg.get('CodeSize', 0),
                }]}
            else:
                yield {'Versions': []}
        elif self._method == 'list_aliases':
            yield {'Aliases': []}                                                      # no aliases in in-memory store by default


class Lambda__AWS__Client__In_Memory(Lambda__AWS__Client):

    def __init__(self, store: dict = None, url_store: dict = None):
        super().__init__()
        self._store      = store     if store     is not None else {}
        self._url_store  = url_store if url_store is not None else {}
        self._fake       = _Fake_Lambda_Client(self._store, self._url_store)

    def client(self):
        return self._fake


class Lambda__Deployer__In_Memory(Lambda__Deployer):
    """Lambda__Deployer subclass that skips folder zipping and uses the in-memory client."""

    def __init__(self, aws_client: Lambda__AWS__Client__In_Memory):
        super().__init__()
        self._aws_client = aws_client

    def client(self):
        return self._aws_client._fake

    def _zip_folder(self, folder_path: str) -> bytes:
        return b'FAKE_ZIP'                                                             # Skip actual FS access in unit tests
