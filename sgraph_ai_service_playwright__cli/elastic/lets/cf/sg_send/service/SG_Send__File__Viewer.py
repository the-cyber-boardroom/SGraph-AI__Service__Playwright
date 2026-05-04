# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SG_Send__File__Viewer
# Fetches a single CloudFront-realtime .gz from S3, gunzips it, and optionally
# parses the TSV via the existing CF__Realtime__Log__Parser.  Used by the
# diagnostic command `sp el lets cf sg-send view <key>`.
#
# Two outputs:
#   raw_text(bucket, key, region) → str           — gunzipped TSV as-is
#   parsed   (bucket, key, region) → (records, skipped_count)
#                                                — typed Schema__CF__Event__Record list
#
# The viewer reuses the *exact* fetch + gunzip path the loader uses, so what
# you see here is what gets indexed (no surprises).  No mocks; tests subclass
# S3__Object__Fetcher (its `s3_client` seam) or pass canned bytes via a fixture.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser, gunzip
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher          import S3__Object__Fetcher


class SG_Send__File__Viewer(Type_Safe):
    s3_fetcher : S3__Object__Fetcher
    parser     : CF__Realtime__Log__Parser

    def raw_text(self, bucket : str ,
                       key    : str ,
                       region : str = ''
                  ) -> str:                                                          # gunzipped TSV — empty string if file is empty
        gz_bytes = self.s3_fetcher.get_object_bytes(bucket=bucket, key=key, region=region)
        return gunzip(gz_bytes)

    def parsed(self, bucket : str ,
                     key    : str ,
                     region : str = ''
                ) -> Tuple[List__Schema__CF__Event__Record, int]:                    # (records, lines_skipped)
        tsv_text = self.raw_text(bucket=bucket, key=key, region=region)
        return self.parser.parse(tsv_text)
