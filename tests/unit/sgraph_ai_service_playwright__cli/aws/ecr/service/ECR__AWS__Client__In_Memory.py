# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ECR__AWS__Client__In_Memory
# Dict-backed fake boto3 ECR client for unit tests. No mocks. No patches.
#
# Store shape:
#   self._store[repo_name] = {
#       'repo'  : { ... raw describe_repositories dict ... },
#       'images': { digest: { tags, size, pushed_at, manifest, scan } },
#       'lifecycle_policy': str,   # JSON text or ''
#   }
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client import ECR__AWS__Client


class _Fake_ECR_Client:                                                          # Minimal boto3-alike ECR client backed by in-memory dicts

    def __init__(self, store: dict):
        self._store = store

    # ── paginator ─────────────────────────────────────────────────────────────

    def get_paginator(self, method: str):
        return _Fake_Paginator(self, method)

    # ── describe_repositories ────────────────────────────────────────────────

    def describe_repositories(self, repositoryNames=None, **_):
        if repositoryNames:
            missing = [n for n in repositoryNames if n not in self._store]
            if missing:
                raise ClientError(
                    {'Error': {'Code'   : 'RepositoryNotFoundException',
                               'Message': f'Repository not found: {missing[0]}'}},
                    'DescribeRepositories',
                )
            repos = [self._store[n]['repo'] for n in repositoryNames]
        else:
            repos = [v['repo'] for v in self._store.values()]
        return {'repositories': repos}

    # ── describe_images ───────────────────────────────────────────────────────

    def describe_images(self, repositoryName='', imageIds=None, filter=None, **_):
        if repositoryName not in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotFoundException',
                           'Message': f'Repository not found: {repositoryName}'}},
                'DescribeImages',
            )
        images = self._store[repositoryName]['images']
        details = []
        if imageIds:
            for ident in imageIds:
                digest = ident.get('imageDigest')
                tag    = ident.get('imageTag')
                match  = None
                if digest and digest in images:
                    match = (digest, images[digest])
                elif tag:
                    for d, img in images.items():
                        if tag in img.get('tags', []):
                            match = (d, img)
                            break
                if not match:
                    raise ClientError(
                        {'Error': {'Code'   : 'ImageNotFoundException',
                                   'Message': f'Image not found: {ident}'}},
                        'DescribeImages',
                    )
                details.append(self._to_image_detail(*match))
        else:
            for d, img in images.items():
                if filter and filter.get('tagStatus') == 'UNTAGGED':
                    if img.get('tags'):
                        continue
                details.append(self._to_image_detail(d, img))
        return {'imageDetails': details}

    # ── lifecycle policy ──────────────────────────────────────────────────────

    def get_lifecycle_policy(self, repositoryName='', **_):
        if repositoryName not in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotFoundException',
                           'Message': f'Repository not found: {repositoryName}'}},
                'GetLifecyclePolicy',
            )
        policy = self._store[repositoryName].get('lifecycle_policy', '')
        if not policy:
            raise ClientError(
                {'Error': {'Code'   : 'LifecyclePolicyNotFoundException',
                           'Message': 'No lifecycle policy on this repository.'}},
                'GetLifecyclePolicy',
            )
        return {'repositoryName': repositoryName, 'lifecyclePolicyText': policy}

    # ── scan findings ─────────────────────────────────────────────────────────

    def describe_image_scan_findings(self, repositoryName='', imageId=None, **_):
        if repositoryName not in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotFoundException',
                           'Message': f'Repository not found: {repositoryName}'}},
                'DescribeImageScanFindings',
            )
        images = self._store[repositoryName]['images']
        ident  = imageId or {}
        digest = ident.get('imageDigest')
        tag    = ident.get('imageTag')
        target = None
        if digest and digest in images:
            target = (digest, images[digest])
        elif tag:
            for d, img in images.items():
                if tag in img.get('tags', []):
                    target = (d, img)
                    break
        if not target:
            raise ClientError(
                {'Error': {'Code'   : 'ImageNotFoundException',
                           'Message': f'Image not found: {ident}'}},
                'DescribeImageScanFindings',
            )
        d, img = target
        scan = img.get('scan')
        if not scan:
            raise ClientError(
                {'Error': {'Code'   : 'ScanNotFoundException',
                           'Message': f'No scan for {d}'}},
                'DescribeImageScanFindings',
            )
        return {
            'repositoryName'   : repositoryName,
            'imageId'          : {'imageDigest': d,
                                  'imageTag'   : (img.get('tags') or [''])[0]},
            'imageScanStatus'  : {'status': scan.get('status', 'COMPLETE')},
            'imageScanFindings': {
                'imageScanCompletedAt' : scan.get('completed_at',
                                                  datetime.now(timezone.utc)),
                'findingSeverityCounts': scan.get('counts', {}),
            },
        }

    # ── batch_delete_image ────────────────────────────────────────────────────

    def batch_delete_image(self, repositoryName='', imageIds=None, **_):
        if repositoryName not in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotFoundException',
                           'Message': f'Repository not found: {repositoryName}'}},
                'BatchDeleteImage',
            )
        images   = self._store[repositoryName]['images']
        deleted  = []
        failures = []
        for ident in (imageIds or []):
            digest = ident.get('imageDigest')
            tag    = ident.get('imageTag')
            match_digest = None
            if digest and digest in images:
                match_digest = digest
            elif tag:
                for d, img in images.items():
                    if tag in img.get('tags', []):
                        match_digest = d
                        break
            if match_digest is None:
                failures.append({'imageId'     : dict(ident),
                                 'failureCode' : 'ImageNotFound',
                                 'failureReason': 'Image not found'})
                continue
            tags_before = list(images[match_digest].get('tags', []))
            del images[match_digest]
            deleted.append({'imageDigest': match_digest,
                            'imageTag'   : tags_before[0] if tags_before else ''})
        return {'imageIds': deleted, 'failures': failures}

    # ── create_repository / delete_repository ─────────────────────────────────

    def create_repository(self, repositoryName='', imageScanningConfiguration=None, **_):
        if repositoryName in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryAlreadyExistsException',
                           'Message': f'Repository already exists: {repositoryName}'}},
                'CreateRepository',
            )
        scan_cfg = imageScanningConfiguration or {'scanOnPush': False}
        self._store[repositoryName] = {
            'repo': {
                'repositoryName'             : repositoryName,
                'repositoryArn'              : f'arn:aws:ecr:eu-west-2:123456789012:repository/{repositoryName}',
                'registryId'                 : '123456789012',
                'repositoryUri'              : f'123456789012.dkr.ecr.eu-west-2.amazonaws.com/{repositoryName}',
                'createdAt'                  : datetime.now(timezone.utc),
                'imageTagMutability'         : 'MUTABLE',
                'imageScanningConfiguration' : scan_cfg,
            },
            'images'          : {},
            'lifecycle_policy': '',
        }
        return {'repository': self._store[repositoryName]['repo']}

    def delete_repository(self, repositoryName='', force=False, **_):
        if repositoryName not in self._store:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotFoundException',
                           'Message': f'Repository not found: {repositoryName}'}},
                'DeleteRepository',
            )
        if self._store[repositoryName]['images'] and not force:
            raise ClientError(
                {'Error': {'Code'   : 'RepositoryNotEmptyException',
                           'Message': f'Repository not empty: {repositoryName}'}},
                'DeleteRepository',
            )
        removed = self._store.pop(repositoryName)
        return {'repository': removed['repo']}

    # ── internal ──────────────────────────────────────────────────────────────

    def _to_image_detail(self, digest: str, img: dict) -> dict:
        scan = img.get('scan') or {}
        return {
            'registryId'             : '123456789012',
            'repositoryName'         : img.get('repo_name', ''),
            'imageDigest'            : digest,
            'imageTags'              : list(img.get('tags', [])),
            'imageSizeInBytes'       : int(img.get('size', 0)),
            'imagePushedAt'          : img.get('pushed_at',
                                                datetime.now(timezone.utc)),
            'imageManifestMediaType' : img.get('manifest',
                                                'application/vnd.docker.distribution.manifest.v2+json'),
            'imageScanStatus'        : {'status': scan.get('status', '')} if scan else {},
        }


class _Fake_Paginator:
    def __init__(self, client: _Fake_ECR_Client, method: str):
        self._client = client
        self._method = method

    def paginate(self, **kwargs):
        if self._method == 'describe_repositories':
            yield self._client.describe_repositories(repositoryNames=kwargs.get('repositoryNames'))
        elif self._method == 'describe_images':
            yield self._client.describe_images(repositoryName=kwargs.get('repositoryName', ''),
                                               filter        = kwargs.get('filter'))


def _digest_from_name(name: str) -> str:                                         # deterministic digest for seeded test data
    h = hashlib.sha256(name.encode()).hexdigest()
    return f'sha256:{h}'


class ECR__AWS__Client__In_Memory(ECR__AWS__Client):

    def __init__(self):
        super().__init__()
        self._store = {}
        self._fake  = _Fake_ECR_Client(self._store)

    def client(self):
        return self._fake

    # ── seeding helpers ──────────────────────────────────────────────────────

    def seed_repo(self, name: str, image_tag_mutability: str = 'MUTABLE',
                  scan_on_push: bool = False, lifecycle_policy: str = '') -> str:
        self._store[name] = {
            'repo': {
                'repositoryName'             : name,
                'repositoryArn'              : f'arn:aws:ecr:eu-west-2:123456789012:repository/{name}',
                'registryId'                 : '123456789012',
                'repositoryUri'              : f'123456789012.dkr.ecr.eu-west-2.amazonaws.com/{name}',
                'createdAt'                  : datetime.now(timezone.utc),
                'imageTagMutability'         : image_tag_mutability,
                'imageScanningConfiguration' : {'scanOnPush': scan_on_push},
            },
            'images'          : {},
            'lifecycle_policy': lifecycle_policy,
        }
        return name

    def seed_image(self, repo: str, digest: str = '', tags=None,
                   size: int = 1024, pushed_at=None, scan: dict = None) -> str:
        if repo not in self._store:
            self.seed_repo(repo)
        tags = list(tags or [])
        if not digest:
            digest = _digest_from_name(f'{repo}:{",".join(tags) or "untagged"}:{size}')
        self._store[repo]['images'][digest] = dict(
            repo_name = repo,
            tags      = tags,
            size      = size,
            pushed_at = pushed_at or datetime.now(timezone.utc),
            manifest  = 'application/vnd.docker.distribution.manifest.v2+json',
            scan      = scan,
        )
        return digest

    def set_lifecycle_policy(self, repo: str, policy_text: str):
        if repo in self._store:
            self._store[repo]['lifecycle_policy'] = policy_text
