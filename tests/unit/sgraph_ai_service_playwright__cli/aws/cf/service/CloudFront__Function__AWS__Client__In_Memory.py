# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__Function__AWS__Client__In_Memory
# In-memory fake boto3 client for CloudFront Functions. No mocks, no patches.
# Dict-backed; mirrors the create/describe/get/update/publish/delete surface.
# ═══════════════════════════════════════════════════════════════════════════════

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Function__AWS__Client import CloudFront__Function__AWS__Client


def _no_such_function(name: str, op: str) -> ClientError:
    return ClientError({'Error': {'Code': 'NoSuchFunctionExists', 'Message': name}}, op)


class _Fake_CF_Function_Client:
    def __init__(self, store: dict):
        self._store = store                                                          # name -> {code, etag, stage, runtime, comment, arn, status}

    def _summary(self, name: str) -> dict:
        f = self._store[name]
        return {'Name'            : name,
                'Status'          : f['status'],
                'FunctionConfig'  : {'Runtime': f['runtime'], 'Comment': f['comment']},
                'FunctionMetadata': {'FunctionARN': f['arn'], 'Stage': f['stage'], 'LastModifiedTime': '2026-01-01'}}

    def create_function(self, Name, FunctionConfig, FunctionCode, **_):
        if Name in self._store:
            raise ClientError({'Error': {'Code': 'FunctionAlreadyExists', 'Message': Name}}, 'CreateFunction')
        self._store[Name] = {'code': FunctionCode, 'etag': f'ETAG-{Name}-1',
                             'stage': 'DEVELOPMENT', 'runtime': FunctionConfig.get('Runtime', ''),
                             'comment': FunctionConfig.get('Comment', ''),
                             'arn': f'arn:aws:cloudfront::123456789012:function/{Name}', 'status': 'UNPUBLISHED'}
        return {'FunctionSummary': self._summary(Name), 'ETag': self._store[Name]['etag']}

    def describe_function(self, Name, Stage='LIVE', **_):
        if Name not in self._store:
            raise _no_such_function(Name, 'DescribeFunction')
        return {'FunctionSummary': self._summary(Name), 'ETag': self._store[Name]['etag']}

    def get_function(self, Name, Stage='LIVE', **_):
        if Name not in self._store:
            raise _no_such_function(Name, 'GetFunction')
        return {'FunctionCode': self._store[Name]['code'], 'ETag': self._store[Name]['etag']}

    def update_function(self, Name, IfMatch, FunctionConfig, FunctionCode, **_):
        if Name not in self._store:
            raise _no_such_function(Name, 'UpdateFunction')
        f = self._store[Name]
        f['code'] = FunctionCode; f['comment'] = FunctionConfig.get('Comment', f['comment'])
        f['etag'] = f['etag'] + 'u'
        return {'FunctionSummary': self._summary(Name), 'ETag': f['etag']}

    def publish_function(self, Name, IfMatch, **_):
        if Name not in self._store:
            raise _no_such_function(Name, 'PublishFunction')
        f = self._store[Name]; f['stage'] = 'LIVE'; f['status'] = 'DEPLOYED'
        f['arn'] = f['arn']                                                          # LIVE ARN form (same id for the fake)
        return {'FunctionSummary': self._summary(Name), 'ETag': f['etag']}

    def delete_function(self, Name, IfMatch, **_):
        if Name not in self._store:
            raise _no_such_function(Name, 'DeleteFunction')
        del self._store[Name]


class CloudFront__Function__AWS__Client__In_Memory(CloudFront__Function__AWS__Client):

    def __init__(self, store: dict = None):
        super().__init__()
        self._store = store if store is not None else {}
        self._fake  = _Fake_CF_Function_Client(self._store)

    def client(self):
        return self._fake
