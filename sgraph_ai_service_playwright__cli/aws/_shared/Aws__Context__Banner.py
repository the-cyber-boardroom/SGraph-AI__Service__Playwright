# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Aws__Context__Banner
# Resolves the active AWS targeting context (role / region / account_id) and
# renders a one-line dim banner suitable for the top of any sg aws list/show
# command. Helps users verify they are looking at the account & region they
# think they are before they wonder why a list comes back empty.
#
# Resolution order matches the rest of the system:
#   role      : SG_CREDENTIALS__CURRENT_ROLE → Sg__Aws__Context singleton
#   region    : Aws__Region__Resolver (region_flag → role → AWS_DEFAULT_REGION)
#   account   : role config (cached when the role was added) → '?'
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver


class Aws__Context__Banner(Type_Safe):

    def resolve(self, region_flag: str = '') -> dict:                            # dict — role / region / account_id (all str, possibly empty)
        role       = self._current_role()
        region     = str(Aws__Region__Resolver().resolve(region_flag=region_flag))
        account_id = self._account_id_for_role(role)
        return dict(role=role, region=region, account_id=account_id)

    def render(self, region_flag: str = '') -> str:                              # rich-markup one-liner; safe to console.print()
        ctx = self.resolve(region_flag=region_flag)
        role    = ctx['role']    or '(none)'
        region  = ctx['region']  or '(unknown)'
        account = ctx['account_id'] or '?'
        return f'[dim]role:[/] [cyan]{role}[/]  [dim]region:[/] [cyan]{region}[/]  [dim]account:[/] [cyan]{account}[/]'

    def _current_role(self) -> str:
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
        env = os.environ.get('SG_CREDENTIALS__CURRENT_ROLE', '').strip("'\"")
        if env:
            return env
        return Sg__Aws__Context.get_current_role() or ''

    def _account_id_for_role(self, role_name: str) -> str:
        if not role_name:
            return ''
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            config = Credentials__Store().role_get(role_name)
            if config and getattr(config, 'account_id', ''):
                return str(config.account_id)
        except Exception:
            pass
        return ''
