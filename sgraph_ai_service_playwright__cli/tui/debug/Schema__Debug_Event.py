# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui debug: Schema__Debug_Event
# One line in the under-the-hood debug feed: a timestamped, categorised event a
# service recorded while doing work (an S3 list, an object GET, a local write, an AWS
# API call). `detail` carries the optional second line. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Debug_Event(Type_Safe):
    seq      : int   = 0
    ts       : float = 0.0
    category : str                                                                   # e.g. s3.list / s3.get / fs.write / aws.firehose / ui
    message  : str
    detail   : str
    ok       : bool  = True                                                          # False marks an error/warning event
