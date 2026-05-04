# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Synthetic__Data__Generator
# Produces log-shaped documents for seeding a fresh Elastic+Kibana stack so
# `sp elastic seed` has something to display in Kibana Discover immediately.
# Deterministic when given a seed (the "seed" field here is a PRNG seed, NOT
# the `sp elastic seed` CLI command — different concepts, same English word).
#
# The generator is intentionally self-contained: no external feeds, no vaults,
# no S3. That keeps this slice fast to land and easy to test. When the real
# data pipeline (vault → logs, Playwright sessions → events) lands in a later
# slice, the generator stays as the baseline fixture generator used by tests.
# ═══════════════════════════════════════════════════════════════════════════════

import random
from datetime                                                                       import datetime, timedelta, timezone
from typing                                                                         import List as _List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Log__Document   import List__Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Log__Level               import Enum__Log__Level
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Log__Document        import Schema__Log__Document


SERVICES  : _List[str] = ['playwright', 'sidecar', 'mitmproxy', 'kibana', 'elastic', 'fluent-bit']
HOSTS     : _List[str] = ['ip-10-0-1-11', 'ip-10-0-1-12', 'ip-10-0-2-22', 'ip-10-0-3-33']
USERS     : _List[str] = ['alice', 'bob', 'carol', 'dave', 'eve', 'system']
MESSAGES  : _List[str] = ['session started'                ,
                          'page loaded'                    ,
                          'screenshot captured'            ,
                          'timeout while waiting for selector',
                          'navigation finished'            ,
                          'upstream proxy unreachable'     ,
                          'cache hit'                      ,
                          'cache miss'                     ,
                          'auth token rotated'             ,
                          'metrics flushed'                ,
                          'container restarted'            ,
                          'disk usage above threshold'     ]

LEVEL_WEIGHTS = [(Enum__Log__Level.DEBUG, 30),                                      # Skewed toward INFO to match real observability data
                 (Enum__Log__Level.INFO , 55),
                 (Enum__Log__Level.WARN , 10),
                 (Enum__Log__Level.ERROR,  5)]


class Synthetic__Data__Generator(Type_Safe):
    seed        : int = 0                                                           # 0 = non-deterministic; any other value seeds random.Random
    window_days : int = 7

    def generate(self, count: int) -> List__Schema__Log__Document:                  # Timestamps span the last `window_days` days, ending now()
        rng       = random.Random(self.seed) if self.seed else random.Random()
        now       = datetime.now(tz=timezone.utc)
        start     = now - timedelta(days=max(self.window_days, 1))
        span_sec  = int((now - start).total_seconds())
        docs      = List__Schema__Log__Document()

        levels   = [lvl for lvl, w in LEVEL_WEIGHTS for _ in range(w)]              # Expand weights into a uniform pool for random.choice

        for i in range(count):
            offset_sec = rng.randint(0, span_sec)
            ts         = start + timedelta(seconds=offset_sec)
            ts_iso     = ts.strftime('%Y-%m-%dT%H:%M:%S.') + f'{ts.microsecond // 1000:03d}Z'
            docs.append(Schema__Log__Document(timestamp   = ts_iso                   ,
                                              level       = rng.choice(levels)       ,
                                              service     = rng.choice(SERVICES)     ,
                                              host        = rng.choice(HOSTS)        ,
                                              user        = rng.choice(USERS)        ,
                                              message     = rng.choice(MESSAGES)     ,
                                              duration_ms = rng.randint(1, 5000)     ))
        return docs
