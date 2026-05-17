# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Schema__Edit__Diff__Item
#
# One atomic change produced by Edit__Diff.diff(). kind in {'add','remove','modify'}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Edit__Diff__Item(Type_Safe):

    kind      : str = ''    # 'add', 'remove', 'modify'
    namespace : str = ''    # 'roles', 'aws_credentials', 'vault_keys', 'secrets'
    key       : str = ''    # e.g. 'default' or 'default/secret_key'
    old_value : str = ''    # '(none)' for add; '(sealed)' for secrets
    new_value : str = ''    # '(removed)' for delete; '(sealed)' for secrets
