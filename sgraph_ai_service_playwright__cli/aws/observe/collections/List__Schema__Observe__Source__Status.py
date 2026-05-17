# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — List__Schema__Observe__Source__Status
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.observe.schemas.Schema__Observe__Source__Status import Schema__Observe__Source__Status


class List__Schema__Observe__Source__Status(Type_Safe):
    items : List[Schema__Observe__Source__Status]
