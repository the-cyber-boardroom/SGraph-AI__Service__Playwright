# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Progress__Reporter
# Optional collaborator for Events__Loader so the per-file loop can surface
# what it's doing.  This base class is a deliberate no-op — every method is
# `pass` — so existing tests construct the loader without a reporter and the
# loader behaves exactly as before.
#
# The CLI provides a Rich-backed subclass that prints one line per file
# completion (see scripts/elastic_lets.py::Console__Progress__Reporter).
# Future additions: a quiet mode subclass; a JSON-emitting subclass for
# automation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Progress__Reporter(Type_Safe):

    def on_queue_built(self, files_queued: int, queue_mode: str): pass               # Called once after the queue is built and before processing starts

    def on_skip_filter_done(self, before: int, after: int): pass                     # Called once when --skip-processed filtered the queue (before == size before filter, after == size after)

    def on_file_done(self, idx          : int ,                                      # 1-based — "this is file idx of total"
                            total        : int ,
                            key          : str ,
                            events_count : int ,
                            duration_ms  : int ): pass

    def on_file_error(self, idx        : int ,
                             total      : int ,
                             key        : str ,
                             error_msg  : str ): pass

    def on_load_complete(self): pass                                                 # Called once after the per-file loop finishes (before the response is built)
