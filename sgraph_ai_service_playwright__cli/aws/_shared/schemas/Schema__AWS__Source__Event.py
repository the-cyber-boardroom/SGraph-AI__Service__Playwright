# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__AWS__Source__Event
# One normalised row from any observability source (S3, CloudWatch, CloudTrail).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__AWS__Source__Event(Type_Safe):
    timestamp  : str = ''
    source     : str = ''
    stream     : str = ''
    message    : str = ''
    raw        : dict
