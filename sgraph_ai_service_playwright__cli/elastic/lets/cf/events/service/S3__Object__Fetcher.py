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

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter                   import Call__Counter


class S3__Object__Fetcher(Type_Safe):
    counter : Call__Counter                                                         # Auto-instantiates per instance; SG_Send orchestrator injects a shared one

    def s3_client(self, region: str):                                               # Single seam — tests override.  Routes through the shared session factory (role/assume/bare).
        from sgraph_ai_service_playwright__cli.aws._shared.auth.Aws__Session__Factory import boto3_client_via_context
        return boto3_client_via_context('s3', region=region)

    @type_safe
    def get_object_bytes(self, bucket : str ,
                                key    : str ,
                                region : str = ''
                          ) -> bytes:
        client   = self.s3_client(region)
        response = client.get_object(Bucket=bucket, Key=key)
        self.counter.s3()                                                            # One GetObject call
        body     = response.get('Body')
        if body is None:
            return b''
        return body.read()
