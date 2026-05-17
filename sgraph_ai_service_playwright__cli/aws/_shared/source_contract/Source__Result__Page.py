# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Source__Result__Page
# Paged result wrapper returned by Source__Contract.query().
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event import Schema__AWS__Source__Event


class Source__Result__Page(Type_Safe):
    events      : List[Schema__AWS__Source__Event]
    next_token  : str = ''
    total_count : int = 0
    truncated   : bool = False
