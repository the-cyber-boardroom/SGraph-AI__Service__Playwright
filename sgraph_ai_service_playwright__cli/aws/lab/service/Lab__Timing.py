# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Timing
# Wall-clock timer: start/sample/elapsed helpers used by experiments.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Int__Duration_Ms      import Safe_Int__Duration_Ms
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Timing__Sample   import Schema__Lab__Timing__Sample
from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Timing__Sample import List__Schema__Lab__Timing__Sample


class Lab__Timing(Type_Safe):
    _start_ns : int = 0                                                            # monotonic ns at start

    def start(self) -> 'Lab__Timing':
        self._start_ns = time.monotonic_ns()
        return self

    def elapsed_ms(self) -> int:
        if self._start_ns == 0:
            return 0
        return (time.monotonic_ns() - self._start_ns) // 1_000_000

    def sample(self, label: str, success: bool = True, detail: str = '') -> Schema__Lab__Timing__Sample:
        return Schema__Lab__Timing__Sample(
            elapsed_ms = Safe_Int__Duration_Ms(self.elapsed_ms()),
            label      = label,
            success    = success,
            detail     = detail,
        )
