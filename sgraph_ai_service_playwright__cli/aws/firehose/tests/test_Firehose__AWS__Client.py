# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — firehose: Firehose__AWS__Client
# Overrides the boto3 client() seam with a fake that returns canned API shapes — no
# AWS, no mocks. Covers list+describe+streams, S3 destination ARN resolution, and the
# graceful empty path when the client raises (no creds).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.firehose.service.Firehose__AWS__Client import Firehose__AWS__Client


class _FakeBoto:
    def list_delivery_streams(self, **kwargs):
        return {'DeliveryStreamNames': ['sgraph-send-cf-logs-to-s3-2'], 'HasMoreDeliveryStreams': False}

    def describe_delivery_stream(self, DeliveryStreamName=''):
        return {'DeliveryStreamDescription': {
            'DeliveryStreamName'  : DeliveryStreamName,
            'DeliveryStreamStatus': 'ACTIVE',
            'DeliveryStreamType'  : 'DirectPut',
            'CreateTimestamp'     : '2026-01-01',
            'DeliveryStreamARN'   : f'arn:aws:firehose:eu-west-2:745:deliverystream/{DeliveryStreamName}',
            'Destinations'        : [{'ExtendedS3DestinationDescription': {
                'BucketARN': 'arn:aws:s3:::745506449035--sgraph-send-cf-logs--eu-west-2',
                'Prefix'   : 'cloudfront-realtime/'}}]}}


class FakeFirehose(Firehose__AWS__Client):
    def client(self):
        return _FakeBoto()


class RaisingFirehose(Firehose__AWS__Client):
    def client(self):
        raise RuntimeError('Unable to locate credentials')


class test_Firehose__AWS__Client(TestCase):

    def test_list_and_streams(self):
        streams = FakeFirehose().streams()
        assert len(streams) == 1
        s = streams[0]
        assert s.name               == 'sgraph-send-cf-logs-to-s3-2'
        assert s.status             == 'ACTIVE'
        assert s.stream_type        == 'DirectPut'
        assert s.destination_bucket == '745506449035--sgraph-send-cf-logs--eu-west-2'
        assert s.destination_prefix == 'cloudfront-realtime/'
        assert s.arn.startswith('arn:aws:firehose')

    def test_describe(self):
        s = FakeFirehose().describe_delivery_stream('sgraph-send-cf-logs-to-s3-2')
        assert s is not None
        assert s.destination_bucket.endswith('cf-logs--eu-west-2')

    def test_graceful_when_no_creds(self):
        client = RaisingFirehose()
        assert client.list_delivery_streams()                == []
        assert client.describe_delivery_stream('x')          is None
        assert list(client.streams())                        == []
