# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Token
# SG/Role wire form: parse/format, whole-API '*', capability + resource coverage, expiry.
# Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Token         import Tui_Api__Token


def _grant(api, capability, resource='*'):
    return Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api=api, capability=capability, resource=resource))


def test_parse_format_roundtrip():
    token = Tui_Api__Token()
    grant = token.parse('sg-aws.s3:read')
    assert str(grant.scope.api)        == 'sg-aws.s3'
    assert str(grant.scope.capability) == 'read'
    assert str(grant.scope.resource)   == '*'
    assert token.format(grant)         == 'sg-aws.s3:read:*'


def test_parse_with_resource_keeps_extra_colons():
    token = Tui_Api__Token()
    grant = token.parse('sg-edge.slugs:write:alice')
    assert str(grant.scope.capability) == 'write'
    assert str(grant.scope.resource)   == 'alice'


def test_parse_whole_api_star():
    grant = Tui_Api__Token().parse('sg-aws.s3:*')
    assert str(grant.scope.capability) == '*'


def test_covers_capability_strict_and_star():
    token      = Tui_Api__Token()
    need_read  = Schema__Tui_Api__Scope(api='sg-aws.s3', capability='read')
    need_write = Schema__Tui_Api__Scope(api='sg-aws.s3', capability='write')
    assert token.covers(_grant('sg-aws.s3', 'read'),  need_read)  is True
    assert token.covers(_grant('sg-aws.s3', 'read'),  need_write) is False        # narrower capability
    assert token.covers(_grant('sg-aws.s3', '*'),     need_write) is True         # whole-API grant
    assert token.covers(_grant('sg-aws.ec2', 'read'), need_read)  is False        # different API


def test_covers_resource_glob():
    token = Tui_Api__Token()
    need  = Schema__Tui_Api__Scope(api='sg-edge.slugs', capability='write', resource='alice')
    assert token.covers(_grant('sg-edge.slugs', 'write', 'al*'),  need) is True
    assert token.covers(_grant('sg-edge.slugs', 'write', 'bob*'), need) is False


def test_is_expired():
    token = Tui_Api__Token()
    bound = _grant('a', 'read'); bound.expires_at = 100.0
    assert token.is_expired(bound, 200.0) is True
    assert token.is_expired(bound, 50.0)  is False
    assert token.is_expired(_grant('a', 'read'), 10_000.0) is False               # expires_at 0 = never
