# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — ECR__AWS__Client
# Thin boto3('ecr') boundary for read-only ECR queries:
#   - list_repositories         → paginated describe_repositories
#   - describe_repository(name) → repo + lifecycle policy + aggregated metrics
#   - list_images(repo)         → paginated describe_images
#   - describe_image(repo, ref) → one Schema__ECR__Image (ref = tag or digest)
#   - get_image_scan_findings   → most-recent severity counts
#
# Mutation methods (Slice 2 — gated at the CLI layer by
# SG_AWS__ECR__ALLOW_MUTATIONS):
#   - delete_image(repo, tag_or_digest)
#   - batch_delete_images(repo, digests)
#   - create_repository(name)
#   - delete_repository(name, force=False)
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from botocore.exceptions import ClientError
from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.collections.List__Schema__ECR__Image  import List__Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.collections.List__Schema__ECR__Repo   import List__Schema__ECR__Repo
from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status     import Enum__ECR__Image_Scan_Status
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Tag          import Safe_Str__ECR__Tag
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Image             import Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Repo              import Schema__ECR__Repo
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Scan_Finding_Counts import Schema__ECR__Scan_Finding_Counts
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Scan_Findings     import Schema__ECR__Scan_Findings
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session            import Sg__Aws__Session


class ECR__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                            # cached session — injected or lazy-init via setup()

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                            # Single seam — subclass overrides for in-memory tests
        self.setup()
        return self.session.boto3_client_from_context('ecr')

    # ── read: repositories ───────────────────────────────────────────────────

    def list_repositories(self) -> List__Schema__ECR__Repo:
        ecr       = self.client()
        result    = List__Schema__ECR__Repo()
        paginator = ecr.get_paginator('describe_repositories')
        for page in paginator.paginate():
            for raw in page.get('repositories', []):
                result.append(self._parse_repo(raw))
        return result

    def describe_repository(self, repo_name: str) -> Optional[Schema__ECR__Repo]:
        try:
            ecr  = self.client()
            resp = ecr.describe_repositories(repositoryNames=[repo_name])
            repos = resp.get('repositories', [])
            if not repos:
                return None
            schema = self._parse_repo(repos[0])
            # ── lifecycle policy (optional) ─────────────────────────────────
            try:
                lp = ecr.get_lifecycle_policy(repositoryName=repo_name)
                schema.lifecycle_policy = lp.get('lifecyclePolicyText', '') or ''
            except ClientError as exc:
                code = exc.response.get('Error', {}).get('Code', '')
                if code != 'LifecyclePolicyNotFoundException':
                    raise
            # ── aggregate image_count + total_size_bytes ────────────────────
            count = 0
            total = 0
            img_paginator = ecr.get_paginator('describe_images')
            for page in img_paginator.paginate(repositoryName=repo_name):
                for img in page.get('imageDetails', []):
                    count += 1
                    total += int(img.get('imageSizeInBytes', 0) or 0)
            schema.image_count      = count
            schema.total_size_bytes = total
            return schema
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'RepositoryNotFoundException':
                return None
            raise

    # ── read: images ─────────────────────────────────────────────────────────

    def list_images(self, repo_name: str, untagged: bool = False) -> Optional[List__Schema__ECR__Image]:
        try:
            ecr       = self.client()
            result    = List__Schema__ECR__Image()
            paginator = ecr.get_paginator('describe_images')
            kwargs    = {'repositoryName': repo_name}
            if untagged:
                kwargs['filter'] = {'tagStatus': 'UNTAGGED'}
            for page in paginator.paginate(**kwargs):
                for raw in page.get('imageDetails', []):
                    result.append(self._parse_image(repo_name, raw))
            return result
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'RepositoryNotFoundException':
                return None
            raise

    def describe_image(self, repo_name: str, tag_or_digest: str) -> Optional[Schema__ECR__Image]:
        try:
            ecr   = self.client()
            ident = self._image_identifier(tag_or_digest)
            resp  = ecr.describe_images(repositoryName=repo_name, imageIds=[ident])
            details = resp.get('imageDetails', [])
            if not details:
                return None
            return self._parse_image(repo_name, details[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('RepositoryNotFoundException', 'ImageNotFoundException'):
                return None
            raise

    # ── read: scan findings ──────────────────────────────────────────────────

    def get_image_scan_findings(self, repo_name: str, tag_or_digest: str
                                ) -> Optional[Schema__ECR__Scan_Findings]:
        try:
            ecr   = self.client()
            ident = self._image_identifier(tag_or_digest)
            resp  = ecr.describe_image_scan_findings(repositoryName=repo_name,
                                                     imageId=ident)
            digest_raw   = resp.get('imageId', {}).get('imageDigest', '') or ''
            status_raw   = resp.get('imageScanStatus', {}).get('status', '') or ''
            findings_raw = resp.get('imageScanFindings', {}) or {}
            completed    = findings_raw.get('imageScanCompletedAt', '')
            completed_s  = str(completed) if completed else ''
            counts_raw   = findings_raw.get('findingSeverityCounts', {}) or {}
            counts = Schema__ECR__Scan_Finding_Counts(
                critical      = int(counts_raw.get('CRITICAL',      0)),
                high          = int(counts_raw.get('HIGH',          0)),
                medium        = int(counts_raw.get('MEDIUM',        0)),
                low           = int(counts_raw.get('LOW',           0)),
                informational = int(counts_raw.get('INFORMATIONAL', 0)),
                undefined     = int(counts_raw.get('UNDEFINED',     0)),
            )
            try:
                status = Enum__ECR__Image_Scan_Status(status_raw)
            except ValueError:
                status = Enum__ECR__Image_Scan_Status.UNKNOWN
            return Schema__ECR__Scan_Findings(
                repo_name    = Safe_Str__ECR__Repo_Name(repo_name) if repo_name else Safe_Str__ECR__Repo_Name(''),
                digest       = Safe_Str__ECR__Image_Digest(digest_raw) if digest_raw else Safe_Str__ECR__Image_Digest(''),
                status       = status,
                completed_at = completed_s,
                counts       = counts,
            )
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('RepositoryNotFoundException',
                        'ImageNotFoundException',
                        'ScanNotFoundException'):
                return None
            raise

    # ── mutate: images ───────────────────────────────────────────────────────

    def delete_image(self, repo_name: str, tag_or_digest: str) -> bool:
        try:
            ecr   = self.client()
            ident = self._image_identifier(tag_or_digest)
            resp  = ecr.batch_delete_image(repositoryName=repo_name, imageIds=[ident])
            deleted  = resp.get('imageIds', []) or []
            failures = resp.get('failures',  []) or []
            if not deleted and failures:
                code = failures[0].get('failureCode', '')
                if code in ('ImageNotFound', 'ImageReferencedByManifestList'):
                    return False
            return bool(deleted)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('RepositoryNotFoundException', 'ImageNotFoundException'):
                return False
            raise

    def batch_delete_images(self, repo_name: str, digests: list) -> int:
        if not digests:
            return 0
        try:
            ecr        = self.client()
            image_ids  = [{'imageDigest': d} for d in digests]
            resp       = ecr.batch_delete_image(repositoryName=repo_name, imageIds=image_ids)
            return len(resp.get('imageIds', []) or [])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'RepositoryNotFoundException':
                return 0
            raise

    # ── mutate: repositories ─────────────────────────────────────────────────

    def create_repository(self, name: str) -> bool:
        try:
            ecr = self.client()
            ecr.create_repository(repositoryName             = name,
                                  imageScanningConfiguration = {'scanOnPush': True})
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'RepositoryAlreadyExistsException':
                return False
            raise

    def delete_repository(self, name: str, force: bool = False) -> bool:
        try:
            ecr = self.client()
            ecr.delete_repository(repositoryName=name, force=force)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'RepositoryNotFoundException':
                return False
            raise

    # ── internal ─────────────────────────────────────────────────────────────

    def _image_identifier(self, tag_or_digest: str) -> dict:                    # ECR imageIdentifier: imageDigest if sha256:, else imageTag
        if tag_or_digest.startswith('sha256:'):
            return {'imageDigest': tag_or_digest}
        return {'imageTag': tag_or_digest}

    def _parse_repo(self, raw: dict) -> Schema__ECR__Repo:
        name        = raw.get('repositoryName', '')
        created_raw = raw.get('createdAt')
        created_s   = str(created_raw) if created_raw else ''
        scan_cfg    = raw.get('imageScanningConfiguration', {}) or {}
        return Schema__ECR__Repo(
            name                 = Safe_Str__ECR__Repo_Name(name) if name else Safe_Str__ECR__Repo_Name(''),
            arn                  = raw.get('repositoryArn',  '') or '',
            registry_id          = raw.get('registryId',     '') or '',
            created_at           = created_s,
            image_tag_mutability = raw.get('imageTagMutability', '') or '',
            scan_on_push         = bool(scan_cfg.get('scanOnPush', False)),
        )

    def _parse_image(self, repo_name: str, raw: dict) -> Schema__ECR__Image:
        digest_raw  = raw.get('imageDigest', '') or ''
        tag_strings = raw.get('imageTags', []) or []
        size_bytes  = int(raw.get('imageSizeInBytes', 0) or 0)
        pushed_raw  = raw.get('imagePushedAt')
        pushed_s    = str(pushed_raw) if pushed_raw else ''
        manifest    = raw.get('imageManifestMediaType', '') or ''
        scan_raw    = raw.get('imageScanStatus', {}) or {}
        scan_str    = scan_raw.get('status', '') or ''
        try:
            scan_status = Enum__ECR__Image_Scan_Status(scan_str)
        except ValueError:
            scan_status = Enum__ECR__Image_Scan_Status.UNKNOWN
        tags = [Safe_Str__ECR__Tag(t) for t in tag_strings if t]
        return Schema__ECR__Image(
            repo_name           = Safe_Str__ECR__Repo_Name(repo_name) if repo_name else Safe_Str__ECR__Repo_Name(''),
            digest              = Safe_Str__ECR__Image_Digest(digest_raw) if digest_raw else Safe_Str__ECR__Image_Digest(''),
            tags                = tags,
            size_bytes          = size_bytes,
            pushed_at           = pushed_s,
            manifest_media_type = manifest,
            scan_status         = scan_status,
        )
