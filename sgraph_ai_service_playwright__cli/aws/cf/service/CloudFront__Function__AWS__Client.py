# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__Function__AWS__Client
# Sole boto3 boundary for CloudFront Functions (the JS-based viewer/origin
# request hooks; distinct from Lambda@Edge).
#
# EXCEPTION — see CloudFront__AWS__Client header. CloudFront Functions are
# global; all calls go via us-east-1.
#
# Stage values: 'DEVELOPMENT' (default after create/update) and 'LIVE' (after
# publish). Distributions must associate the function via its qualified ARN
# at the LIVE stage.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

import boto3                                                                          # EXCEPTION — see module header
from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Function            import Schema__CF__Function


class CloudFront__Function__AWS__Client(Type_Safe):

    def client(self):                                                                  # Single boto3 seam — subclass overrides to inject fake
        return boto3.client('cloudfront', region_name='us-east-1')

    # ── read ─────────────────────────────────────────────────────────────────

    def describe(self, name: str, stage: str = 'LIVE') -> Schema__CF__Function:
        try:
            resp = self.client().describe_function(Name=name, Stage=stage)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'NoSuchFunctionExists':
                return Schema__CF__Function(name=name, exists=False)
            raise
        return self._parse(resp.get('FunctionSummary', {}), etag=resp.get('ETag', ''))

    def get_code(self, name: str, stage: str = 'LIVE') -> str:
        try:
            resp = self.client().get_function(Name=name, Stage=stage)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'NoSuchFunctionExists':
                return ''
            raise
        raw = resp.get('FunctionCode', b'')
        # botocore returns FunctionCode as a StreamingBody (file-like) — must
        # .read() to get the actual bytes. Falling back to str() returned the
        # object repr "<botocore.response.StreamingBody object at 0x…>" and
        # silently broke every drift check.
        if hasattr(raw, 'read'):
            raw = raw.read()
        if isinstance(raw, (bytes, bytearray)):
            return raw.decode('utf-8', errors='replace')
        return str(raw)

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, name: str, code: str, comment: str = '',
               runtime: str = 'cloudfront-js-2.0') -> Schema__CF__Function:
        resp = self.client().create_function(
            Name           = name,
            FunctionConfig = {'Comment': comment, 'Runtime': runtime},
            FunctionCode   = code.encode('utf-8'),
        )
        return self._parse(resp.get('FunctionSummary', {}), etag=resp.get('ETag', ''))

    def update(self, name: str, code: str, etag: str, comment: str = '',
               runtime: str = 'cloudfront-js-2.0') -> Schema__CF__Function:
        resp = self.client().update_function(
            Name           = name,
            IfMatch        = etag,
            FunctionConfig = {'Comment': comment, 'Runtime': runtime},
            FunctionCode   = code.encode('utf-8'),
        )
        return self._parse(resp.get('FunctionSummary', {}), etag=resp.get('ETag', ''))

    def publish(self, name: str, etag: str) -> Schema__CF__Function:
        resp = self.client().publish_function(Name=name, IfMatch=etag)
        return self._parse(resp.get('FunctionSummary', {}), etag=resp.get('ETag', ''))

    def delete(self, name: str, etag: str) -> bool:
        try:
            self.client().delete_function(Name=name, IfMatch=etag)
            return True
        except ClientError:
            return False

    # ── internal ─────────────────────────────────────────────────────────────

    def _parse(self, summary: dict, etag: str = '') -> Schema__CF__Function:
        cfg = summary.get('FunctionConfig', {})
        meta = summary.get('FunctionMetadata', {})
        return Schema__CF__Function(
            name          = summary.get('Name', ''),
            arn           = meta.get('FunctionARN', ''),
            stage         = meta.get('Stage', ''),
            status        = summary.get('Status', ''),
            runtime       = cfg.get('Runtime', ''),
            comment       = cfg.get('Comment', ''),
            etag          = etag,
            last_modified = str(meta.get('LastModifiedTime', '')),
            exists        = bool(summary.get('Name', '')),
        )
