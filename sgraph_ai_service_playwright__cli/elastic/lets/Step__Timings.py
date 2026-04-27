# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Step__Timings
# Per-file timing breakdown captured during Events__Loader's per-file loop.
# Used by Progress__Reporter.on_file_done so the operator can see WHERE the
# wall time is spent — diagnoses "is it S3 latency, gunzip, parsing, or
# bulk-post?" without instrumenting their own stopwatch.
#
# All values in milliseconds.  Zero means "not measured" (e.g. parse_ms is 0
# on an empty file because the parser short-circuits).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Step__Timings(Type_Safe):
    s3_get_ms          : int = 0                                                    # GetObject network round-trip + body.read()
    gunzip_ms          : int = 0                                                    # gzip.decompress + UTF-8 decode
    parse_ms           : int = 0                                                    # CF__Realtime__Log__Parser.parse (TSV split + Stage 1 derivations)
    bulk_post_ms       : int = 0                                                    # Cumulative across per-day batches
    manifest_update_ms : int = 0                                                    # Inventory _update_by_query

    def total(self) -> int:                                                         # Sum of all measured steps — should approximately equal the file's wall_ms
        return (self.s3_get_ms + self.gunzip_ms + self.parse_ms +
                self.bulk_post_ms + self.manifest_update_ms)

    def render_compact(self) -> str:                                                # "(s3:280 gz:2 parse:5 post:38 mark:2)" — for inline display in the progress line
        return (f's3:{self.s3_get_ms} '
                f'gz:{self.gunzip_ms} '
                f'parse:{self.parse_ms} '
                f'post:{self.bulk_post_ms} '
                f'mark:{self.manifest_update_ms}')
