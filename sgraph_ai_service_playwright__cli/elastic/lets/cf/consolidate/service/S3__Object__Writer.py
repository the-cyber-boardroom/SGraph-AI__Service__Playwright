# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Object__Writer
# Single boto3 boundary for `s3:PutObject`.  Sibling of S3__Object__Fetcher.
# One responsibility:
#   put_object_bytes(bucket, key, body, region) → (version_id, etag, error)
# Returns the S3 VersionId and ETag from the PutObject response so callers can
# record the exact object that was written (for manifest compat checking).
#
# Decision #11: the ONLY new boto3 surface in the consolidation slice.
# Tests subclass and override put_object_bytes(); no boto3, no AWS round trips.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — same narrow S3 boundary pattern as S3__Object__Fetcher

from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter                   import Call__Counter


class S3__Object__Writer(Type_Safe):
    counter : Call__Counter

    def s3_client(self, region: str):                                               # Single seam — tests override.  Empty region falls through to boto3 default chain.
        if region:
            return boto3.client('s3', region_name=region)
        return boto3.client('s3')

    @type_safe
    def put_object_bytes(self, bucket  : str   ,
                                key    : str   ,
                                body   : bytes ,
                                region : str   = ''
                          ) -> Tuple[str, str, str]:                                # (version_id, etag, error_message)
        client = self.s3_client(region)
        try:
            response = client.put_object(Bucket=bucket, Key=key, Body=body)
            self.counter.s3()
            version_id = str(response.get('VersionId', '') or '')
            etag       = str(response.get('ETag'     , '') or '').strip('"')
            return version_id, etag, ''
        except Exception as exc:
            return '', '', str(exc)[:300]
