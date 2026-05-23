# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Log__Sink
# The AWS log sink: wraps S3__AWS__Client, one JSON object per record under the
# shared key layout (identical to Local_FS so trace/replay match local vs AWS).
# Sentinel writes its own clean format straight to S3 — no Kinesis/Firehose.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket                  import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                          import S3__AWS__Client
from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Log_Record import List__Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record           import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink                      import Log__Sink


class S3__Log__Sink(Log__Sink):
    bucket    : Safe_Str__S3__Bucket
    s3_client : S3__AWS__Client

    def write(self, record: Schema__Sentinel__Log_Record) -> str:
        key  = self.key_for(record)
        body = json.dumps(record.json(), indent=2).encode('utf-8')
        self.s3_client.put_object(str(self.bucket), key, body, content_type='application/json')
        return key

    def read_all(self) -> List__Schema__Sentinel__Log_Record:
        resp    = self.s3_client.list_objects(str(self.bucket), str(self.prefix), recursive=True)
        records = List__Schema__Sentinel__Log_Record()
        for obj in sorted(resp.objects, key=lambda o: str(o.key)):
            body = self.s3_client.get_object_body(str(self.bucket), str(obj.key))
            if body:
                records.append(Schema__Sentinel__Log_Record.from_json(json.loads(body)))
        return records
