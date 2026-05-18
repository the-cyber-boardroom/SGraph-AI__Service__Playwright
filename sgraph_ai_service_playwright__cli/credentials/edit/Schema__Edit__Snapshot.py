# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Schema__Edit__Snapshot
#
# Parsed representation of a TOML edit buffer. Returned by Toml__Parser.
# '********' values mean "unchanged — do not write back to keyring".
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


SENTINEL = '********'                                                            # placeholder for sealed secrets


class Schema__Edit__Snapshot(Type_Safe):

    roles           : dict = None    # {name: {region, assume_role_arn, session_name}}
    aws_credentials : dict = None    # {role: {access_key, secret_key}}  — '********' = unchanged
    vault_keys      : dict = None    # {name: value}  — '********' = unchanged
    secrets         : dict = None    # {ns: {name: value}}  — '********' = unchanged

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.roles           is None: self.roles           = {}
        if self.aws_credentials is None: self.aws_credentials = {}
        if self.vault_keys      is None: self.vault_keys      = {}
        if self.secrets         is None: self.secrets         = {}
