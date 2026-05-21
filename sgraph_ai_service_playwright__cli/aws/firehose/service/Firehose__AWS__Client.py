# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — firehose: Firehose__AWS__Client
# Read-only access to Amazon Data Firehose (no CRUD — we only need to retrieve the
# CF-logging delivery streams and their S3 destinations to complete the architecture
# picture). Sole Firehose boundary — subclasses override client() to inject fakes for
# tests. List/describe never raise: a missing credential yields [] / None so callers
# (CLI, architecture screen) degrade gracefully. Credentials flow through the shared
# Aws__Session__Factory (keyring role / assume / bare-boto3 fall-through).
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.aws.firehose.schemas.List__Firehose__Stream    import List__Firehose__Stream
from sgraph_ai_service_playwright__cli.aws.firehose.schemas.Schema__Firehose__Stream  import Schema__Firehose__Stream


class Firehose__AWS__Client(Type_Safe):
    region : str = ''                                                                 # override to target a specific region

    def client(self):                                                                 # single boto3 seam — subclass overrides to inject a fake
        from sgraph_ai_service_playwright__cli.aws._shared.auth.Aws__Session__Factory import boto3_client_via_context
        return boto3_client_via_context('firehose', region=self.region)

    def list_delivery_streams(self) -> list:                                          # returns list[str] of stream names; never raises
        try:
            fh     = self.client()
            names  = []
            kwargs = {'Limit': 100}
            while True:
                resp = fh.list_delivery_streams(**kwargs)
                names.extend(resp.get('DeliveryStreamNames', []))
                if not resp.get('HasMoreDeliveryStreams') or not names:
                    break
                kwargs['ExclusiveStartDeliveryStreamName'] = names[-1]
            return names
        except Exception:
            return []

    def describe_delivery_stream(self, name : str) -> Optional[Schema__Firehose__Stream]:
        try:
            resp = self.client().describe_delivery_stream(DeliveryStreamName=name)
        except Exception:
            return None
        return self.parse_description(resp.get('DeliveryStreamDescription', {}) or {})

    def streams(self) -> List__Firehose__Stream:                                      # list + describe each → the full read picture
        out = List__Firehose__Stream()
        for name in self.list_delivery_streams():
            stream = self.describe_delivery_stream(name)
            if stream is not None:
                out.append(stream)
        return out

    def parse_description(self, d : dict) -> Schema__Firehose__Stream:
        bucket = ''
        prefix = ''
        dests  = d.get('Destinations', []) or []
        if dests:
            ext    = dests[0].get('ExtendedS3DestinationDescription') or dests[0].get('S3DestinationDescription') or {}
            bucket = (ext.get('BucketARN', '') or '').replace('arn:aws:s3:::', '')
            prefix = ext.get('Prefix', '') or ''
        return Schema__Firehose__Stream(name               = d.get('DeliveryStreamName', '')   or '',
                                        status             = d.get('DeliveryStreamStatus', '') or '',
                                        stream_type        = d.get('DeliveryStreamType', '')   or '',
                                        created            = str(d.get('CreateTimestamp', '')),
                                        destination_bucket = bucket,
                                        destination_prefix = prefix,
                                        arn                = d.get('DeliveryStreamARN', '')     or '')
