# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — List__Schema__Source__Stream__Ref
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Ref import Schema__Source__Stream__Ref


class List__Schema__Source__Stream__Ref(Type_Safe):
    items : List[Schema__Source__Stream__Ref]
