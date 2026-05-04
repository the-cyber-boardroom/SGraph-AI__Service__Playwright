# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — S3__Object__Fetcher__In_Memory
# Real subclass of S3__Object__Fetcher that returns canned bytes from a
# fixture dict instead of calling boto3.  Mirrors S3__Inventory__Lister__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher import S3__Object__Fetcher


class S3__Object__Fetcher__In_Memory(S3__Object__Fetcher):
    fixture_objects : dict                                                          # {(bucket, key): bytes} OR {key: bytes} for single-bucket tests
    get_calls       : list                                                          # [(bucket, key, region), ...]

    def get_object_bytes(self, bucket : str ,
                                key    : str ,
                                region : str = ''
                          ) -> bytes:
        self.get_calls.append((bucket, key, region))
        # Try (bucket, key) tuple first, then key-only fallback
        if (bucket, key) in self.fixture_objects:
            return self.fixture_objects[(bucket, key)]
        if key in self.fixture_objects:
            return self.fixture_objects[key]
        raise KeyError(f'no fixture for ({bucket!r}, {key!r})')                      # Fail loud — tests should pre-populate fixture_objects
