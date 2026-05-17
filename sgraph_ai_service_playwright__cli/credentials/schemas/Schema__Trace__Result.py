# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__Trace__Result
# Output of Credentials__Resolver.trace() dry-run.
# Pure data — no methods. No AWS calls involved in producing this.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Trace__Result(Type_Safe):
    command_path      : list    # list[str] — original command words
    matched_route     : str     # e.g. 'aws lambda *'
    matched_role      : str     # e.g. 'deploy-lambda'
    role_chain        : list    # list[str] — ['default', 'admin'] for assume-role chain
    would_assume_arn  : str     # empty if static creds
    session_name_tmpl : str     # e.g. 'sg-deploy-lambda-<ts>-<uuid>' (dry-run)
    source_creds      : str     # e.g. 'keyring (sg.aws.default.access_key)' or 'not found'
