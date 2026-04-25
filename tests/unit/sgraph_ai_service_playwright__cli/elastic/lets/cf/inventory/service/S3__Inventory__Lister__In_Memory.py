# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — S3__Inventory__Lister__In_Memory
# Real subclass of S3__Inventory__Lister that returns canned pages from
# fixture_pages instead of calling boto3. Mirrors the pattern set by
# Elastic__AWS__Client__In_Memory and Elastic__HTTP__Client__In_Memory.
# Records every paginate() call so tests can assert on the (bucket, prefix,
# max_keys, region) tuple.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List, Tuple

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister


class S3__Inventory__Lister__In_Memory(S3__Inventory__Lister):
    fixture_pages    : list                                                         # List[List[dict]] — one inner list per page; each dict is one S3 object
    paginate_calls   : list                                                         # [(bucket, prefix, max_keys, region), ...]

    def paginate(self, bucket   : str ,
                       prefix   : str = ''  ,
                       max_keys : int = 0   ,
                       region   : str = ''
                  ) -> Tuple[List[dict], int]:
        self.paginate_calls.append((bucket, prefix, max_keys, region))
        objects: List[dict] = []
        pages_listed        = 0
        for page in self.fixture_pages:
            pages_listed += 1
            for obj in page:
                objects.append(obj)
                if max_keys and len(objects) >= max_keys:                           # Mirror real lister's mid-page stop semantics
                    return objects, pages_listed
        return objects, pages_listed
