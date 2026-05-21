# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — firehose: List__Firehose__Stream
# Typed list of Schema__Firehose__Stream. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.firehose.schemas.Schema__Firehose__Stream import Schema__Firehose__Stream


class List__Firehose__Stream(Type_Safe__List):
    expected_type = Schema__Firehose__Stream
