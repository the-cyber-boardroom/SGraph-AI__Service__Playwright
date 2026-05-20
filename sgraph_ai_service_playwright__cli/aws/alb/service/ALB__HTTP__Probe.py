# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__HTTP__Probe
# One HTTP GET via urllib.request; captures status/duration/size or error.
# Caller drives the retry loop — this class never retries.
# ═══════════════════════════════════════════════════════════════════════════════

import time
import urllib.request

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Probe__Result import Schema__ALB__Perf_Test__Probe__Result


class ALB__HTTP__Probe(Type_Safe):
    timeout_s : int = 30
    _calls    : int = 0

    def probe(self, url: str) -> Schema__ALB__Perf_Test__Probe__Result:
        self._calls += 1
        t0     = time.monotonic()
        result = Schema__ALB__Perf_Test__Probe__Result(attempt=self._calls)
        try:
            with urllib.request.urlopen(url, timeout=int(self.timeout_s)) as resp:  # noqa: S310 — operator-supplied URL via perf-test
                body  = resp.read() or b''
                result.status_code = int(resp.status)
                result.body_size   = len(body)
        except urllib.error.HTTPError as exc:                                       # 4xx/5xx still return a response
            result.status_code = int(exc.code)
            try:
                body            = exc.read() or b''
                result.body_size = len(body)
            except Exception:                                                       # noqa: BLE001
                result.body_size = 0
        except Exception as exc:                                                    # noqa: BLE001 — network failure / timeout
            result.status_code = 0
            result.error       = f'{exc.__class__.__name__}: {exc}'
        result.duration_ms = int((time.monotonic() - t0) * 1000)
        return result
