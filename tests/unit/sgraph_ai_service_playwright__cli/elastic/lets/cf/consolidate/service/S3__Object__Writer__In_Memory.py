# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — S3__Object__Writer__In_Memory
# Real subclass of S3__Object__Writer that stores written bytes in memory
# instead of calling boto3.  Mirrors S3__Object__Fetcher__In_Memory.
#
# `put_calls` records every write for assertion in tests.
# `written`   holds the latest body per (bucket, key) for content verification.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Tuple

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.S3__Object__Writer import S3__Object__Writer


class S3__Object__Writer__In_Memory(S3__Object__Writer):
    put_calls : list                                                                # [(bucket, key, len(body), region), ...]
    written   : dict                                                                # {(bucket, key): bytes} — last write wins

    def put_object_bytes(self, bucket  : str   ,
                                key    : str   ,
                                body   : bytes ,
                                region : str   = ''
                          ) -> Tuple[str, str, str]:                                # (version_id, etag, error_message)
        self.put_calls.append((bucket, key, len(body), region))
        self.written[(bucket, key)] = body
        return '', f'inmemory-etag-{len(body)}', ''
