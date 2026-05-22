# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Privilege__Resolver
# Grant coverage + expiry; backing-privilege checks over a temp creds catalogue
# (no AWS, no boto3). Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue       import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Priv_Kind     import Enum__Tui_Api__Priv_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action    import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant     import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Privilege import Schema__Tui_Api__Privilege
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope     import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver


def _resolver(tmp_path):
    catalogue = Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 'scopes.json'))
    return Tui_Api__Privilege__Resolver(creds_catalogue=catalogue), catalogue


def _action(api='sg-aws.s3', capability='read', resource='*'):
    return Schema__Tui_Api__Action(name='list_objects',
                                  scope=Schema__Tui_Api__Scope(api=api, capability=capability, resource=resource))


def _grant(api, capability, expires_at=0.0):
    grant = Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api=api, capability=capability))
    grant.expires_at = expires_at
    return grant


def test_grants_cover_exact_star_and_wrong(tmp_path):
    resolver, _ = _resolver(tmp_path)
    action = _action()
    assert resolver.grants_cover([_grant('sg-aws.s3', 'read')],  action) is True
    assert resolver.grants_cover([_grant('sg-aws.s3', '*')],     action) is True
    assert resolver.grants_cover([_grant('sg-aws.ec2', 'read')], action) is False
    assert resolver.grants_cover([],                             action) is False


def test_grants_cover_respects_expiry(tmp_path):
    resolver, _ = _resolver(tmp_path)
    action  = _action()
    expired = _grant('sg-aws.s3', 'read', expires_at=100.0)
    assert resolver.grants_cover([expired], action, now=200.0) is False
    assert resolver.grants_cover([expired], action, now=50.0)  is True


def test_missing_sg_role_absent_then_present(tmp_path):
    resolver, catalogue = _resolver(tmp_path)
    privilege = Schema__Tui_Api__Privilege(kind=Enum__Tui_Api__Priv_Kind.SG_ROLE, ref='s3-read')
    assert 'sg aws creds scope add' in resolver.missing(privilege)
    catalogue.scope_add('s3-read', 'arn:aws:iam::123456789012:role/s3-read', '1h')
    assert resolver.missing(privilege) == ''


def test_missing_iam_policy_returns_parseable_minimal_policy(tmp_path):
    resolver, _ = _resolver(tmp_path)
    privilege = Schema__Tui_Api__Privilege(kind=Enum__Tui_Api__Priv_Kind.IAM_POLICY, ref='s3:ListBucket')
    policy = json.loads(resolver.hint(privilege))
    assert policy['Statement'][0]['Action'] == 's3:ListBucket'


def test_missing_env_privilege(tmp_path):
    resolver, _ = _resolver(tmp_path)
    privilege = Schema__Tui_Api__Privilege(kind=Enum__Tui_Api__Priv_Kind.ENV, ref='SG_TUI_API_TEST_FLAG')
    os.environ.pop('SG_TUI_API_TEST_FLAG', None)
    assert 'set environment variable' in resolver.missing(privilege)
    os.environ['SG_TUI_API_TEST_FLAG'] = '1'
    try:
        assert resolver.missing(privilege) == ''
    finally:
        os.environ.pop('SG_TUI_API_TEST_FLAG', None)
