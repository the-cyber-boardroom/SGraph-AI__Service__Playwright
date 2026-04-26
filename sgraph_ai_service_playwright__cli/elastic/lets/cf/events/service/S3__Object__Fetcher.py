# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Object__Fetcher
# Single boto3 boundary for `s3:GetObject`.  One responsibility:
#   get_object_bytes(bucket, key, region) → bytes
# Returns the raw (gzipped) object body; caller is responsible for gunzipping.
#
# Mirrors S3__Inventory__Lister's pattern: per-call client instantiation,
# empty region falls through to boto3's standard chain (slice 1 lesson —
# region_name='' produces a malformed "https://s3..amazonaws.com" endpoint).
#
# Tests subclass and override get_object_bytes(); no boto3, no AWS round trips.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — see slice 1's S3__Inventory__Lister header (mirrors Elastic__AWS__Client)

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe


class S3__Object__Fetcher(Type_Safe):

    def s3_client(self, region: str):                                               # Single seam — tests override.  Empty region falls through to boto3 default chain.
        if region:
            return boto3.client('s3', region_name=region)
        return boto3.client('s3')

    @type_safe
    def get_object_bytes(self, bucket : str ,
                                key    : str ,
                                region : str = ''
                          ) -> bytes:
        client   = self.s3_client(region)
        response = client.get_object(Bucket=bucket, Key=key)
        body     = response.get('Body')
        if body is None:
            return b''
        return body.read()
