# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__Source__Stats
# Aggregation result returned by Source__Contract.stats().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Source__Stats(Type_Safe):
    stream      : str = ''
    aggregation : str = ''
    window_from : str = ''
    window_to   : str = ''
    buckets     : list
    total       : int = 0
