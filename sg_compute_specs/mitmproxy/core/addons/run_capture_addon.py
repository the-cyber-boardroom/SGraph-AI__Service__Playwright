# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Per-run capture addon
#
# Duck-typed mitmproxy addon (no mitmproxy imports at module load time). Groups
# completed flows by the X-SG-Run-Id request header into an in-process ring buffer
# (RUN_CAPTURE). Routes__Capture reads that buffer to serve
# GET /capture/network-log/{run_id} as NDJSON — the per-run addressability the
# user-journey workers need to aggregate flows across N runs.
#
# Only flows that carry X-SG-Run-Id are buffered (keeps it scoped to journey runs).
# The buffer is bounded by run count and per-run record count to cap memory.
# ═══════════════════════════════════════════════════════════════════════════════

from collections import OrderedDict

HEADER__RUN_ID          = 'X-SG-Run-Id'                                             # workers inject this on every browser request
MAX_RUNS                = 256                                                       # distinct run_ids retained (oldest evicted)
MAX_RECORDS_PER_RUN     = 2000                                                      # flows retained per run (oldest evicted)


class Run__Capture__Buffer:                                                         # bounded in-memory store, keyed by run_id

    def __init__(self):
        self.runs = OrderedDict()                                                   # run_id -> list[dict] (insertion-ordered)

    def record(self, run_id, flow_record):
        bucket = self.runs.get(run_id)
        if bucket is None:
            bucket           = []
            self.runs[run_id] = bucket
            while len(self.runs) > MAX_RUNS:                                         # evict oldest run when over the cap
                self.runs.popitem(last=False)
        bucket.append(flow_record)
        while len(bucket) > MAX_RECORDS_PER_RUN:                                     # evict oldest record within a run
            del bucket[0]
        return flow_record

    def records_for(self, run_id):
        return list(self.runs.get(run_id, []))

    def run_ids(self):
        return list(self.runs.keys())

    def clear(self, run_id=None):
        if run_id is None: self.runs.clear()
        else             : self.runs.pop(run_id, None)


RUN_CAPTURE = Run__Capture__Buffer()                                                # shared in-process with the admin API


def _headers_dict(carrier):                                                         # mitmproxy Headers (multidict) or plain dict → dict
    headers = getattr(carrier, 'headers', {}) or {}
    try   : return dict(headers)
    except Exception: return {}


class Run_Capture:                                                                  # the duck-typed addon

    def response(self, flow):
        try:
            run_id = flow.request.headers.get(HEADER__RUN_ID)
        except Exception:
            return
        if not run_id:
            return                                                                  # only journey-tagged traffic is buffered

        request  = flow.request
        response = getattr(flow, 'response', None)
        record   = {'run_id'         : str(run_id)                                              ,
                    'request'        : {'url'        : str(getattr(request, 'url', '')),
                                        'method'     : getattr(request, 'method', None),
                                        'headers'    : _headers_dict(request)         },
                    'response'       : {'status_code': getattr(response, 'status_code', None),
                                        'headers'    : _headers_dict(response)        },
                    'timestamp_start': getattr(request, 'timestamp_start', None)                }
        RUN_CAPTURE.record(str(run_id), record)


addons = [Run_Capture()]                                                            # mitmweb -s <registry> loads this
