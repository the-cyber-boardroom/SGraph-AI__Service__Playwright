# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Lambda__Dependencies__Loader  (slated for upstream into osbot_aws)
# Replaces osbot_aws.aws.lambda_.boto3__lambda.load_dependencies().
# Single STS call. Single S3 download. Single extraction. /tmp warm-cache reuse.
#
# Pairs with Lambda__Dependencies__Builder (same package). The Builder pip-installs
# the pinned dependency list as platform-correct manylinux wheels, strips, zips,
# and uploads ONE content-addressable archive to S3; this Loader pulls + extracts
# that one archive at cold start and prepends it to sys.path.
#
# boto3 used directly (not osbot-aws) on purpose — this pair is infra plumbing
# destined to live in osbot_aws itself; keep it standalone (stdlib + boto3 only).
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import io
import os
import sys
import time
import zipfile


def _deps_hash(packages):                       # Stable hash of a package list — changes only when deps change
    canonical = '|'.join(sorted(packages))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def versioned_name(base_name, packages):        # Combined zip name: base + hash of package list
    return f'{base_name}-{_deps_hash(packages)}'


def _ms(start):                                 # Milliseconds since start (for cold-start profiling)
    return f'{(time.time() - start) * 1000:.0f}ms'


class Lambda__Dependencies__Loader:
    def __init__(self, combined_name):
        self.combined_name = combined_name      # e.g. 'sg-compute-vault-publish-admin-abc123def456'

    def _account_id(self):
        import boto3
        return boto3.client('sts').get_caller_identity()['Account']

    def _region(self):
        import boto3
        return boto3.session.Session().region_name

    def _bucket_name(self):
        return f'{self._account_id()}--osbot-lambdas--{self._region()}'

    def _s3_key(self):
        return f'lambdas-dependencies-combined/{self.combined_name}.zip'

    def _temp_folder(self):
        return f'/tmp/lambdas-dependencies-combined/{self.combined_name}'

    def load(self):
        if os.getenv('AWS_REGION') is None:                       # Not inside Lambda — skip (local imports from venv)
            return None

        t0          = time.time()
        temp_folder = self._temp_folder()

        if temp_folder in sys.path:                               # Already loaded in this container
            return f'{self.combined_name} (already in path)'

        if os.path.exists(temp_folder):                           # Extracted in /tmp — warm container reuse
            sys.path.insert(0, temp_folder)
            print(f'[deps] /tmp cache hit — {_ms(t0)}')
            return f'{self.combined_name} (loaded from /tmp cache)'

        import boto3                                              # Single STS call — not per package
        t_sts      = time.time()
        account_id = boto3.client('sts').get_caller_identity()['Account']
        region     = boto3.session.Session().region_name
        bucket     = f'{account_id}--osbot-lambdas--{region}'
        print(f'[deps] STS get_caller_identity — {_ms(t_sts)}')

        t_s3      = time.time()
        s3        = boto3.client('s3')
        response  = s3.get_object(Bucket=bucket, Key=self._s3_key())   # Single S3 download
        zip_bytes = response['Body'].read()
        print(f'[deps] S3 download ({len(zip_bytes)//1024}KB) — {_ms(t_s3)}')

        t_unzip = time.time()
        os.makedirs(temp_folder, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:   # Single extraction
            zip_ref.extractall(temp_folder)
        print(f'[deps] zip extraction — {_ms(t_unzip)}')

        sys.path.insert(0, temp_folder)
        print(f'[deps] total load — {_ms(t0)}')
        return f'{self.combined_name} (loaded from S3)'


def load_combined_dependency(base_name, packages):                # Drop-in entry point for the handler
    name = versioned_name(base_name, packages)
    return Lambda__Dependencies__Loader(name).load()
