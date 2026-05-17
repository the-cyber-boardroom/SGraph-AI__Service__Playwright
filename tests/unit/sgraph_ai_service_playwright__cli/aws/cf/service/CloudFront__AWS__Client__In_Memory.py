# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__AWS__Client__In_Memory
# In-memory fake boto3 CloudFront client for unit tests.
# Overrides client() so CloudFront__AWS__Client never touches the network.
# No mocks. No patches. Dict-backed dispatch.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client import CloudFront__AWS__Client


class _Fake_CF_Client:
    """Minimal boto3-alike CloudFront client backed by a shared dict store."""

    _counter = 0                                                                       # Class-level monotonic counter for unique IDs

    def __init__(self, store: dict):
        self._store   = store                                                          # Shared distribution store
        self._configs = {}                                                             # Stores ETag → config mapping

    def _etag(self, dist_id: str) -> str:
        return f'ETAG-{dist_id}'

    def list_distributions(self, **_):
        items = list(self._store.values())
        return {'DistributionList': {'Items': items, 'IsTruncated': False, 'Quantity': len(items)}}

    def get_distribution(self, Id: str):
        dist = self._store.get(Id)
        if not dist:
            raise Exception(f'No such distribution: {Id}')
        return {'Distribution': {**dist, 'DistributionConfig': self._configs.get(Id, {})},
                'ETag': self._etag(Id)}

    def get_distribution_config(self, Id: str):
        if Id not in self._store:
            raise Exception(f'No such distribution: {Id}')
        config = self._configs.get(Id, {'Enabled': True})
        return {'DistributionConfig': config, 'ETag': self._etag(Id)}

    def create_distribution(self, DistributionConfig: dict):
        _Fake_CF_Client._counter += 1
        dist_id  = f'E{_Fake_CF_Client._counter:013d}'
        domain   = f'{dist_id.lower()}.cloudfront.net'
        entry    = {
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

    def update_distribution(self, Id: str, DistributionConfig: dict, IfMatch: str):
        if Id not in self._store:
            raise Exception(f'No such distribution: {Id}')
        self._store[Id]['Enabled'] = DistributionConfig.get('Enabled', True)
        self._configs[Id]          = DistributionConfig
        return {'Distribution': self._store[Id], 'ETag': self._etag(Id)}

    def delete_distribution(self, Id: str, IfMatch: str):
        if Id not in self._store:
            raise Exception(f'No such distribution: {Id}')
        if self._store[Id].get('Enabled', True):
            raise Exception(f'Distribution {Id} must be disabled before deletion')
        del self._store[Id]
        self._configs.pop(Id, None)

    def set_deployed(self, dist_id: str):                                             # Test helper — skip ~15 min propagation
        if dist_id in self._store:
            self._store[dist_id]['Status'] = 'Deployed'


class CloudFront__AWS__Client__In_Memory(CloudFront__AWS__Client):

    def __init__(self, store: dict = None):
        super().__init__()
        self._store      = store if store is not None else {}
        self._fake_client = _Fake_CF_Client(self._store)

    def client(self):
        return self._fake_client

    def set_deployed(self, dist_id: str):                                             # Shortcut for tests that don't want to wait
        self._fake_client.set_deployed(dist_id)
