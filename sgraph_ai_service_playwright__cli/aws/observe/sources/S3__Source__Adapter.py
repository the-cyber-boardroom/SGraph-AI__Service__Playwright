# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — S3__Source__Adapter
# Source__Contract adapter backed by S3__AWS__Client.
# Buckets are treated as streams; tail = list most-recent objects;
# query = prefix / key-name substring search.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Enum__Source__Aggregation      import Enum__Source__Aggregation
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stats          import Schema__Source__Stats
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Ref    import Schema__Source__Stream__Ref
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Schema import Schema__Source__Stream__Schema, Schema__Source__Field
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract               import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query                  import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page           import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream                 import Source__Stream
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event             import Schema__AWS__Source__Event
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                            import S3__AWS__Client


class S3__Source__Adapter(Source__Contract):
    client     : S3__AWS__Client
    _connected : bool = False

    def connect(self) -> bool:
        try:
            self.client.list_buckets()
            self._connected = True
            return True
        except Exception:
            return False

    def list_streams(self) -> list:                                     # each bucket is a stream
        try:
            buckets = self.client.list_buckets()
        except Exception:
            return []
        refs = []
        for b in buckets:
            name = b if isinstance(b, str) else b.get('Name', '')
            refs.append(Schema__Source__Stream__Ref(name=name, description='S3 bucket'))
        return refs

    def tail(self, stream: str, since: str) -> Source__Stream:          # stream = bucket name
        def _gen():
            try:
                objects = self.client.list_objects(bucket=stream, max_keys=50)
            except Exception:
                return
            for obj in objects:
                key          = obj if isinstance(obj, str) else obj.get('Key', '')
                last_mod     = '' if isinstance(obj, str) else str(obj.get('LastModified', ''))
                yield Schema__AWS__Source__Event(
                    timestamp = last_mod,
                    source    = 's3',
                    stream    = stream,
                    message   = key,
                    raw       = obj if isinstance(obj, dict) else {'key': obj},
                )
        return Source__Stream(source='s3', stream=stream).with_generator(_gen())

    def query(self, q: Source__Query) -> Source__Result__Page:
        bucket = q.stream or q.source
        try:
            objects = self.client.list_objects(bucket=bucket, prefix=q.text, max_keys=q.limit)
        except Exception:
            return Source__Result__Page()
        events = []
        for obj in objects:
            key      = obj if isinstance(obj, str) else obj.get('Key', '')
            last_mod = '' if isinstance(obj, str) else str(obj.get('LastModified', ''))
            events.append(Schema__AWS__Source__Event(
                timestamp = last_mod,
                source    = 's3',
                stream    = bucket,
                message   = key,
                raw       = obj if isinstance(obj, dict) else {'key': obj},
            ))
        return Source__Result__Page(events=events, total_count=len(events))

    def stats(self, stream: str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats:
        try:
            objects = self.client.list_objects(bucket=stream, max_keys=1000)
        except Exception:
            objects = []
        return Schema__Source__Stats(
            stream      = stream,
            aggregation = agg.value if hasattr(agg, 'value') else str(agg),
            total       = len(objects),
            buckets     = [],
        )

    def schema(self, stream: str) -> Schema__Source__Stream__Schema:
        fields = [
            Schema__Source__Field(name='Key',          type_hint='str',      nullable=False),
            Schema__Source__Field(name='LastModified', type_hint='datetime', nullable=True),
            Schema__Source__Field(name='Size',         type_hint='int',      nullable=True),
            Schema__Source__Field(name='ETag',         type_hint='str',      nullable=True),
        ]
        return Schema__Source__Stream__Schema(stream=stream, fields=fields)
