# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Manifest__Builder
# Assembles a Schema__Consolidated__Manifest from the data gathered during a
# Consolidate__Loader run.  Pure logic — no I/O.  Called once per day after the
# events.ndjson.gz has been written and bytes_written is known.
#
# Decision #5c: run-specific data lives in manifest.json; compat-region metadata
# lives separately in lets-config.json.  This class owns only the former.
# Decision #6: the manifest is also indexed as a doc in sg-cf-consolidated-{date}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidated__Manifest import Schema__Consolidated__Manifest


class Manifest__Builder(Type_Safe):

    def build(self,                                                                 # Construct a fully-populated manifest
              run_id                : str ,
              date_iso              : str ,
              source_count          : int ,
              event_count           : int ,
              bucket                : str ,
              s3_output_key         : str ,
              bytes_written         : int ,
              parser_version        : str ,
              bot_classifier_version: str ,
              compat_region         : str ,
              started_at            : str ,
              finished_at           : str ,
              consolidated_at       : str ,
             ) -> Schema__Consolidated__Manifest:
        return Schema__Consolidated__Manifest(
            run_id                 = run_id                 ,
            date_iso               = date_iso               ,
            source_count           = source_count           ,
            event_count            = event_count            ,
            bucket                 = bucket                 ,
            s3_output_key          = s3_output_key          ,
            bytes_written          = bytes_written          ,
            parser_version         = parser_version         ,
            bot_classifier_version = bot_classifier_version ,
            compat_region          = compat_region          ,
            started_at             = started_at             ,
            finished_at            = finished_at            ,
            consolidated_at        = consolidated_at        ,
        )
