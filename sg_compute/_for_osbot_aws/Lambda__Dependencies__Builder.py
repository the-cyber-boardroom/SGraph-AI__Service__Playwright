# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Lambda__Dependencies__Builder  (slated for upstream into osbot_aws)
# Build-time counterpart to Lambda__Dependencies__Loader.
# pip install ALL deps into one dir → strip → zip → upload one zip to S3.
# Content-addressable: S3 key includes a hash of the package list (idempotent).
#
# The platform/python/abi triple MUST match the target Lambda runtime exactly, or
# native wheels (pydantic-core etc.) fail to import at cold start. SG/Compute
# Lambdas deploy python3.12 / x86_64 (see Setup__Lambda EXPECTED_RUNTIME +
# Lambda__Deployer create_function which omits Architectures → AWS default x86_64).
#
# boto3 used directly on purpose — see Loader header.
# ═══════════════════════════════════════════════════════════════════════════════

import io
import os
import shutil
import subprocess
import zipfile

from sg_compute._for_osbot_aws.Lambda__Dependencies__Loader import versioned_name


class Lambda__Dependencies__Builder:
    BASE_BUCKET_INFIX   = 'osbot-lambdas'                   # bucket: {account}--osbot-lambdas--{region}
    LAMBDA_PLATFORM     = 'manylinux2014_x86_64'            # glibc 2.17 / x86_64 — matches Lambda AL2023 base
    LAMBDA_PYTHON       = '3.12'                             # MUST match Lambda runtime (Enum__Lambda__Runtime.PYTHON_3_12)
    LAMBDA_ABI          = 'cp312'                            # cpython 3.12

    LAMBDA_RUNTIME_PACKAGES = {'boto3', 'botocore', 's3transfer', 'jmespath', 'dateutil', 'six', 'urllib3'}

    def __init__(self, base_name, packages):
        self.base_name = base_name                          # e.g. 'sg-compute-vault-publish-admin'
        self.packages  = list(packages)                     # full pinned package list

    def combined_name(self):
        return versioned_name(self.base_name, self.packages)

    def s3_key(self):
        return f'lambdas-dependencies-combined/{self.combined_name()}.zip'

    def _bucket_name(self):
        import boto3
        account_id = boto3.client('sts').get_caller_identity()['Account']
        region     = boto3.session.Session().region_name
        return f'{account_id}--{self.BASE_BUCKET_INFIX}--{region}'

    def _s3_exists(self, s3_client, bucket):
        try:
            s3_client.head_object(Bucket=bucket, Key=self.s3_key())
            return True
        except Exception:
            return False

    def _build(self):                                       # pip install targeting the Lambda platform
        target_dir = f'/tmp/combined-deps-build/{self.combined_name()}'
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir)

        subprocess.run(
            ['pip', 'install',
             '--target'        , target_dir            ,
             '--platform'      , self.LAMBDA_PLATFORM  ,
             '--python-version', self.LAMBDA_PYTHON    ,
             '--implementation', 'cp'                  ,
             '--abi'           , self.LAMBDA_ABI       ,
             '--only-binary=:all:'                     ,
             '--quiet'                                 ,
             ] + self.packages,
            check=True
        )
        return target_dir

    def _strip(self, directory):                            # Remove clutter + runtime-provided packages
        for root, dirs, files in os.walk(directory, topdown=True):
            to_delete = []
            for d in dirs:
                if d == '__pycache__':
                    to_delete.append(d)
                elif d.endswith('.dist-info'):              # keep METADATA, delete the rest
                    dist_dir = os.path.join(root, d)
                    for f in os.listdir(dist_dir):
                        if f != 'METADATA':
                            fp = os.path.join(dist_dir, f)
                            (shutil.rmtree if os.path.isdir(fp) else os.remove)(fp)
                elif root == directory and d in self.LAMBDA_RUNTIME_PACKAGES:
                    to_delete.append(d)
            for d in to_delete:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
            dirs[:] = [d for d in dirs if d not in to_delete]

            for f in files:
                if f.endswith(('.pyc', '.pyo', '.pyi')):
                    os.remove(os.path.join(root, f))

        bin_dir = os.path.join(directory, 'bin')            # CLI entry-point scripts — not useful in Lambda
        if os.path.isdir(bin_dir):
            shutil.rmtree(bin_dir)

    def _zip_dir(self, directory):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    arcname  = os.path.relpath(filepath, directory)
                    zf.write(filepath, arcname)
        return buf.getvalue()

    def upload(self, force=False):                          # Build + upload; skip if already in S3
        import boto3
        bucket = self._bucket_name()
        s3     = boto3.client('s3')

        if not force and self._s3_exists(s3, bucket):
            return dict(status='skipped', combined_name=self.combined_name(),
                        s3_key=self.s3_key(), reason='already exists in S3')

        target_dir = self._build()
        self._strip(target_dir)
        zip_bytes  = self._zip_dir(target_dir)
        shutil.rmtree(target_dir, ignore_errors=True)

        s3.put_object(Bucket=bucket, Key=self.s3_key(), Body=zip_bytes)
        return dict(status='uploaded', combined_name=self.combined_name(),
                    s3_key=self.s3_key(), size_bytes=len(zip_bytes))
