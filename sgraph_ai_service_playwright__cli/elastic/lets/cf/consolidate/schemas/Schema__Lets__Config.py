# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lets__Config
# Shape of the `lets-config.json` written at the root of each LETS
# compatibility-region folder.  The config is the compat boundary signal:
# everything under a given compat-region folder was produced by the same
# toolchain described here.  Readers check this before touching artefacts.
#
# Decision #5: one file at compat-region root, not filename-versioned.
# Decision #5b: events load --from-consolidated validates this before reading.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type import Enum__Lets__Workflow__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket    import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix


class Schema__Lets__Config(Type_Safe):
    config_version         : Safe_Str__Text                = Safe_Str__Text('1')
    workflow_type          : Enum__Lets__Workflow__Type     = Enum__Lets__Workflow__Type.UNKNOWN

    # ─── input source (flat — avoids nested Type_Safe) ────────────────────────
    input_type             : Safe_Str__Text                                          # "s3"
    input_bucket           : Safe_Str__S3__Bucket
    input_prefix           : Safe_Str__S3__Key__Prefix                               # "cloudfront-realtime/"
    input_format           : Safe_Str__Text                                          # "cf-realtime-tsv-gz"

    # ─── output format ────────────────────────────────────────────────────────
    output_type            : Safe_Str__Text                                          # "ndjson-gz"
    output_schema          : Safe_Str__Text                                          # "Schema__CF__Event__Record"
    output_schema_version  : Safe_Str__Text                                          # "v1"
    output_compression     : Safe_Str__Text                                          # "gzip"

    # ─── implementations (version-stamped at write time) ──────────────────────
    parser                 : Safe_Str__Text                                          # "CF__Realtime__Log__Parser"
    parser_version         : Safe_Str__Text
    bot_classifier         : Safe_Str__Text                                          # "Bot__Classifier"
    bot_classifier_version : Safe_Str__Text
    consolidator           : Safe_Str__Text                                          # "Consolidate__Loader"
    consolidator_version   : Safe_Str__Text

    # ─── metadata ─────────────────────────────────────────────────────────────
    created_at             : Safe_Str__Text                                          # ISO-8601 UTC
    created_by             : Safe_Str__Text                                          # "sp el lets cf consolidate load (run {run_id})"
