# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — aws shared auth: transparent assume (context + resolver + factory)
# No AWS: a real Sg__Aws__Session subclass returns a fake assumed session. Covers the
# active-family context, the resolver assuming the family role + notifying once + caching,
# the "already the scoped role → no assume" short-circuit, and the factory falling back
# to the base identity when assume is not possible.
# ═══════════════════════════════════════════════════════════════════════════════

import io
from contextlib import redirect_stderr
from unittest   import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.auth                       import AWS__Auth__Context as ctx
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Resolver   import AWS__Auth__Resolver, clear_cache
from sgraph_ai_service_playwright__cli.aws._shared.auth.Aws__Session__Factory import boto3_client_via_context
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session   import Sg__Aws__Session
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context   import Sg__Aws__Context


class _FakeAssumedSession:
    def client(self, service, region_name=None):
        return ('assumed-client', service, region_name)


class _FakeSgSession(Sg__Aws__Session):                                              # real subclass — overrides only the STS-touching methods
    def account_id_via_sts(self, base_session=None):
        return '123456789012'
    def assume_arn(self, role_arn, base_session=None):
        return _FakeAssumedSession()


class test_AWS__Auth__Context(TestCase):
    def test_set_get_clear(self):
        assert ctx.get_active_family() == ''
        ctx.set_active_family('el-lets-cf')
        assert ctx.get_active_family() == 'el-lets-cf'
        ctx.clear_active_family()
        assert ctx.get_active_family() == ''


class test_AWS__Auth__Resolver(TestCase):

    def setUp(self):
        clear_cache()
        Sg__Aws__Context.clear_global_role()

    def tearDown(self):
        clear_cache()
        Sg__Aws__Context.clear_global_role()

    def test_assumes_family_role_and_notifies_once(self):
        resolver = AWS__Auth__Resolver(session=_FakeSgSession())
        err = io.StringIO()
        with redirect_stderr(err):
            c1 = resolver.client_for_family('el-lets-cf', 's3', region='eu-west-2')
            c2 = resolver.client_for_family('el-lets-cf', 'sts')
        assert c1 == ('assumed-client', 's3', 'eu-west-2')
        assert c2 == ('assumed-client', 'sts', None)
        assert err.getvalue().count('assuming least-privilege role: sg-lets-cf') == 1   # notice once per process

    def test_unknown_family_returns_none(self):
        assert AWS__Auth__Resolver(session=_FakeSgSession()).client_for_family('nope', 's3') is None

    def test_already_scoped_role_short_circuits(self):
        Sg__Aws__Context.set_global_role('sg-lets-cf')                                # base identity IS the family role → no assume
        assert AWS__Auth__Resolver(session=_FakeSgSession()).client_for_family('el-lets-cf', 's3') is None

    def test_no_account_id_returns_none(self):
        class _NoAccount(_FakeSgSession):
            def account_id_via_sts(self, base_session=None): return ''
        assert AWS__Auth__Resolver(session=_NoAccount()).client_for_family('el-lets-cf', 's3') is None


class test_factory_fallback(TestCase):

    def setUp(self):
        clear_cache()
        ctx.clear_active_family()
        Sg__Aws__Context.clear_global_role()

    def tearDown(self):
        ctx.clear_active_family()

    def test_active_family_falls_back_to_bare_when_assume_impossible(self):
        ctx.set_active_family('el-lets-cf')                                          # real resolver: no creds → no account → None → bare boto3
        client = boto3_client_via_context('s3', region='eu-west-2')
        assert client.meta.region_name == 'eu-west-2'                                # got a real (bare) s3 client, no crash
