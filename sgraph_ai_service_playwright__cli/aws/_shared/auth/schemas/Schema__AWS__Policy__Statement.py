# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: Schema__AWS__Policy__Statement
# One IAM policy statement in a role profile: the actions a command family needs and
# the resources they touch. Renders straight into an IAM policy document. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__AWS__Policy__Statement(Type_Safe):
    sid       : str
    effect    : str  = 'Allow'
    actions   : list                                                                 # e.g. ['s3:GetObject']
    resources : list                                                                 # e.g. ['arn:aws:s3:::bucket/*']
