# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Edit__Diff
#
# Compares two Schema__Edit__Snapshot instances (before vs after) and returns
# a Schema__Edit__Diff listing each atomic change.
# '********' values in the after snapshot mean "unchanged — skip".
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot            import Schema__Edit__Snapshot, SENTINEL
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Diff                import Schema__Edit__Diff
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Diff__Item          import Schema__Edit__Diff__Item


_SEALED_NAMESPACES = {'vault_keys', 'secrets'}                                   # values in these are always '(sealed)' in display


def _item(kind: str, namespace: str, key: str,
          old_value: str, new_value: str) -> Schema__Edit__Diff__Item:
    return Schema__Edit__Diff__Item(kind      = kind      ,
                                    namespace = namespace ,
                                    key       = key       ,
                                    old_value = old_value ,
                                    new_value = new_value )


class Edit__Diff(Type_Safe):

    def diff(self, before: Schema__Edit__Snapshot,
             after:  Schema__Edit__Snapshot) -> Schema__Edit__Diff:
        result = Schema__Edit__Diff()

        self._diff_roles           (before, after, result)
        self._diff_aws_credentials (before, after, result)
        self._diff_vault_keys      (before, after, result)
        self._diff_secrets         (before, after, result)

        result.has_changes = len(result.items) > 0
        return result

    # ── roles ─────────────────────────────────────────────────────────────────

    def _diff_roles(self, before: Schema__Edit__Snapshot,
                    after:  Schema__Edit__Snapshot,
                    result: Schema__Edit__Diff) -> None:
        b = before.roles or {}
        a = after.roles  or {}
        all_keys = set(b) | set(a)
        for name in sorted(all_keys):
            if name not in b:
                result.items.append(_item('add'   , 'roles', name, '(none)', str(a[name])))
            elif name not in a:
                result.items.append(_item('remove', 'roles', name, str(b[name]), '(removed)'))
            else:
                b_cfg = b[name]
                a_cfg = a[name]
                for field in ('region', 'assume_role_arn', 'session_name'):
                    bv = b_cfg.get(field, '')
                    av = a_cfg.get(field, '')
                    if bv != av:
                        result.items.append(
                            _item('modify', 'roles', f'{name}/{field}', bv, av))

    # ── aws credentials ───────────────────────────────────────────────────────

    def _diff_aws_credentials(self, before: Schema__Edit__Snapshot,
                               after:  Schema__Edit__Snapshot,
                               result: Schema__Edit__Diff) -> None:
        b = before.aws_credentials or {}
        a = after.aws_credentials  or {}
        all_roles = set(b) | set(a)
        for role in sorted(all_roles):
            if role not in b:
                result.items.append(_item('add'   , 'aws_credentials', role, '(none)', '(sealed)'))
            elif role not in a:
                result.items.append(_item('remove', 'aws_credentials', role, '(sealed)', '(removed)'))
            else:
                b_creds = b[role]
                a_creds = a[role]
                for field in ('access_key', 'secret_key'):
                    av = a_creds.get(field, '')
                    bv = b_creds.get(field, '')
                    if av == SENTINEL:                                            # user left sentinel — no change
                        continue
                    display_bv = bv if field == 'access_key' and bv.startswith(('AKIA','ASIA','AROA','AIDA')) else '(sealed)'
                    display_av = av if field == 'access_key' and av.startswith(('AKIA','ASIA','AROA','AIDA')) else '(sealed)'
                    if bv != av:
                        result.items.append(
                            _item('modify', 'aws_credentials', f'{role}/{field}',
                                  display_bv, display_av))

    # ── vault keys ────────────────────────────────────────────────────────────

    def _diff_vault_keys(self, before: Schema__Edit__Snapshot,
                          after:  Schema__Edit__Snapshot,
                          result: Schema__Edit__Diff) -> None:
        b = before.vault_keys or {}
        a = after.vault_keys  or {}
        for name in sorted(set(b) | set(a)):
            av = a.get(name, '')
            bv = b.get(name, '')
            if av == SENTINEL:
                continue                                                          # unchanged
            if name not in b:
                result.items.append(_item('add',    'vault_keys', name, '(none)',    '(sealed)'))
            elif name not in a:
                result.items.append(_item('remove', 'vault_keys', name, '(sealed)', '(removed)'))
            elif bv != av:
                result.items.append(_item('modify', 'vault_keys', name, '(sealed)', '(sealed)'))

    # ── secrets ───────────────────────────────────────────────────────────────

    def _diff_secrets(self, before: Schema__Edit__Snapshot,
                       after:  Schema__Edit__Snapshot,
                       result: Schema__Edit__Diff) -> None:
        b = before.secrets or {}
        a = after.secrets  or {}
        all_ns = set(b) | set(a)
        for ns in sorted(all_ns):
            b_ns = b.get(ns, {})
            a_ns = a.get(ns, {})
            for name in sorted(set(b_ns) | set(a_ns)):
                av = a_ns.get(name, '')
                bv = b_ns.get(name, '')
                if av == SENTINEL:
                    continue
                key = f'{ns}/{name}'
                if name not in b_ns:
                    result.items.append(_item('add',    'secrets', key, '(none)',    '(sealed)'))
                elif name not in a_ns:
                    result.items.append(_item('remove', 'secrets', key, '(sealed)', '(removed)'))
                elif bv != av:
                    result.items.append(_item('modify', 'secrets', key, '(sealed)', '(sealed)'))
