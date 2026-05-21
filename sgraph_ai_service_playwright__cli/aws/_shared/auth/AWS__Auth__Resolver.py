# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Auth__Resolver
# Transparent assume. When a command family is active (AWS__Auth__Context), the session
# factory asks the resolver for a client: it assumes that family's least-privilege role
# (from the profile) using the current base identity, prints a one-line notice once per
# process, and caches the assumed session. If the role is absent or the assume is
# denied it returns None — the factory falls back to the base identity and, if that too
# lacks access, the auth guard surfaces the menu (incl. `… iam create`).
#
# Why assume by default: the operator's base identity (SSO / iam-admin / IMDS) is broad;
# every sg el lets cf call should run under the scoped sg-lets-cf role so least-privilege
# is the path of least resistance, not an opt-in.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.auth                            import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session        import Sg__Aws__Session

_SESSION_CACHE : dict = {}                                                           # family → assumed boto3.Session (process lifetime)
_NOTIFIED      : list = []                                                           # families already announced this process


def clear_cache() -> None:                                                           # test hook
    _SESSION_CACHE.clear()
    _NOTIFIED.clear()


class AWS__Auth__Resolver(Type_Safe):
    session : Sg__Aws__Session = None                                                # injectable for tests

    def setup(self):
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client_for_family(self, family : str, service : str, region : str = ''):
        profile = profiles.get_profile(family)
        if profile is None:
            return None
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
        if Sg__Aws__Context.get_current_role() == profile.role_name:                 # already the scoped role → let the normal path handle it
            return None
        assumed = self._assumed_session(family, profile)
        if assumed is None:
            return None
        self._notify_once(family, profile)
        return assumed.client(service, region_name=region) if region else assumed.client(service)

    def _assumed_session(self, family : str, profile):
        if family in _SESSION_CACHE:
            return _SESSION_CACHE[family]
        self.setup()
        account_id = self.session.account_id_via_sts()
        if not account_id:
            return None
        arn     = profiles.role_arn(profile, account_id)
        session = self.session.assume_arn(arn)
        if session is not None:
            _SESSION_CACHE[family] = session
        return session

    def _notify_once(self, family : str, profile) -> None:
        if family in _NOTIFIED:
            return
        _NOTIFIED.append(family)
        print(f'[{family}] assuming least-privilege role: {profile.role_name}', file=sys.stderr)
