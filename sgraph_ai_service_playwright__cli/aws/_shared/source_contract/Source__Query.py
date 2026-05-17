# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Source__Query
# Request shape for a cross-source query.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Source__Query(Type_Safe):
    text       : str = ''
    source     : str = ''
    stream     : str = ''
    since      : str = ''
    until      : str = ''
    limit      : int = 100
    fields     : dict
