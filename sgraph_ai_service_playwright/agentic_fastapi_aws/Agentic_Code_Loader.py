# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_Code_Loader — L2 AWS-aware code loader (v0.1.29)
#
# Resolves WHERE the Python source for the agentic app comes from, BEFORE the
# app FastAPI is imported. Three modes, precedence top-to-bottom:
#
#   1. AGENTIC_CODE_LOCAL_PATH  — local directory / mounted volume. Wins over
#                                 everything. Used for laptop dev and local
#                                 Docker runs with -v.
#   2. AWS_REGION + S3          — inside Lambda. Downloads the pinned zip,
#                                 extracts to /tmp, prepends to sys.path.
#                                 ETag-based warm-invocation cache.
#   3. Passthrough              — nothing matches; use whatever sys.path the
#                                 caller already has (pytest, in-process
#                                 uvicorn).
#
# Returns a human-readable provenance string that gets written to
# AGENTIC_CODE_SOURCE and surfaced on /health/info + /admin/info.
#
# Destined for extraction into a shared package. No app-specific knowledge —
# bucket / key defaults are parameterisable via AGENTIC_CODE_SOURCE_S3_BUCKET
# and AGENTIC_CODE_SOURCE_S3_KEY overrides.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright.consts.env_vars                                   import (ENV_VAR__AGENTIC_APP_NAME              ,
                                                                                            ENV_VAR__AGENTIC_APP_STAGE             ,
                                                                                            ENV_VAR__AGENTIC_APP_VERSION           ,
                                                                                            ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
                                                                                            ENV_VAR__AWS_REGION                    )


CODE_CACHE_ROOT       = '/tmp/agentic-code'                                         # Lambda's only writable scratch; persists across warm invocations
DEFAULT_BUCKET_FORMAT = '{account_id}--sgraph-ai--{region_name}'                    # Matches scripts/package_code.py
DEFAULT_KEY_FORMAT    = 'apps/{app_name}/{stage}/{version}.zip'                     # Matches scripts/package_code.py
PASSTHROUGH_TOKEN     = 'passthrough:sys.path'                                      # Provenance string when no source is configured


def log_s3_fallback(reason: str) -> None:                                           # Stderr -> CloudWatch; surfaces why the agentic Lambda is running baked code
    print(f'[Agentic_Code_Loader] S3 fallback -> passthrough ({reason})', file=sys.stderr)


class Agentic_Code_Loader(Type_Safe):

    def resolve(self) -> str:                                                       # Precedence: local > S3 > passthrough
        return self.load_from_local_path() or self.load_from_s3() or PASSTHROUGH_TOKEN

    def load_from_local_path(self):
        local_path = os.environ.get(ENV_VAR__AGENTIC_CODE_LOCAL_PATH)
        if not local_path:
            return None
        if not os.path.isdir(local_path):
            raise RuntimeError(f'{ENV_VAR__AGENTIC_CODE_LOCAL_PATH} is not a directory: {local_path}')
        sys.path.insert(0, local_path)
        return f'local:{local_path}'

    def resolve_s3_bucket(self, account_id: str, region_name: str) -> str:          # Explicit override > computed default
        override = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET)
        if override:
            return override
        return DEFAULT_BUCKET_FORMAT.format(account_id=account_id, region_name=region_name)

    def resolve_s3_key(self) -> str:                                                # Explicit override > computed from app name / stage / version
        override = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY)
        if override:
            return override
        app_name = os.environ.get(ENV_VAR__AGENTIC_APP_NAME   , '')
        stage    = os.environ.get(ENV_VAR__AGENTIC_APP_STAGE  , '')
        version  = os.environ.get(ENV_VAR__AGENTIC_APP_VERSION, '')
        if not (app_name and stage and version):                                    # Missing one = can't build the key; caller falls through to passthrough
            return ''
        return DEFAULT_KEY_FORMAT.format(app_name=app_name, stage=stage, version=version)

    def load_from_s3(self):                                                         # Soft-fail: any S3 error (NoSuchKey, AccessDenied, transient) → return None so resolve() falls to passthrough and the Lambda boots baked code
        if os.environ.get(ENV_VAR__AGENTIC_CODE_LOCAL_PATH):                        # Local override already handled upstream
            return None
        if not os.environ.get(ENV_VAR__AWS_REGION):                                 # Not on Lambda
            return None
        if not (os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY) or              # Baseline Lambda: on AWS but no S3 coordinates → passthrough
                os.environ.get(ENV_VAR__AGENTIC_APP_NAME)):
            return None

        import boto3, io, zipfile                                                   # Deferred imports — keep module-level import graph minimal
        from botocore.exceptions                                                    import ClientError

        region_name = os.environ[ENV_VAR__AWS_REGION]
        s3_key      = self.resolve_s3_key()
        if not s3_key:
            log_s3_fallback('missing AGENTIC_APP_VERSION/STAGE/NAME — cannot resolve S3 key')
            return None

        try:
            account_id  = boto3.client('sts').get_caller_identity()['Account']
            bucket_name = self.resolve_s3_bucket(account_id, region_name)
            target_dir  = f'{CODE_CACHE_ROOT}/{bucket_name}/{s3_key}'

            if self.cache_is_fresh(target_dir, bucket_name, s3_key):                # Warm-invocation short-circuit — ~200 ms saved per hit
                sys.path.insert(0, target_dir)
                return f's3:{bucket_name}/{s3_key}→{target_dir} (cached)'

            os.makedirs(target_dir, exist_ok=True)
            response  = boto3.client('s3').get_object(Bucket=bucket_name, Key=s3_key)
            zip_bytes = response['Body'].read()
            etag      = response.get('ETag', '').strip('"')

            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
                zip_ref.extractall(target_dir)

            self.write_cache_etag(target_dir, etag)
            sys.path.insert(0, target_dir)
            return f's3:{bucket_name}/{s3_key}→{target_dir}'
        except ClientError as exc:                                                  # NoSuchKey (zip not uploaded yet), AccessDenied, throttling, etc.
            error_code = exc.response.get('Error', {}).get('Code', 'Unknown')
            log_s3_fallback(f'{error_code} on s3 key {s3_key!r}')
            return None
        except zipfile.BadZipFile as exc:                                           # Downloaded something but it's not a valid zip
            log_s3_fallback(f'BadZipFile on s3 key {s3_key!r}: {exc}')
            return None
        except OSError as exc:                                                      # Extraction / filesystem errors (disk full, perms)
            log_s3_fallback(f'OSError extracting {s3_key!r}: {exc}')
            return None

    def cache_is_fresh(self, target_dir: str, bucket_name: str, s3_key: str) -> bool:   # ETag comparison — if S3 object unchanged and cache exists, reuse
        etag_file = os.path.join(target_dir, '.etag')
        if not os.path.exists(etag_file):
            return False
        try:
            import boto3
            head    = boto3.client('s3').head_object(Bucket=bucket_name, Key=s3_key)
            current = head.get('ETag', '').strip('"')
            with open(etag_file, 'r') as f:
                cached = f.read().strip()
            return bool(current) and current == cached
        except Exception:                                                           # Any failure — just re-download; safer than a stale cache hit
            return False

    def write_cache_etag(self, target_dir: str, etag: str) -> None:
        if not etag:
            return
        with open(os.path.join(target_dir, '.etag'), 'w') as f:
            f.write(etag)
