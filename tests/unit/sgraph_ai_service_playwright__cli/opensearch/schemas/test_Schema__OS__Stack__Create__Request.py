# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__OS__Stack__Create__Request
# Defaults + round-trip via .json() so route serialisation stays stable.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request


class test_Schema__OS__Stack__Create__Request(TestCase):

    def test__defaults(self):
        req = Schema__OS__Stack__Create__Request()
        assert str(req.stack_name)     == ''
        assert str(req.region)         == ''
        assert str(req.instance_type)  == ''
        assert str(req.from_ami)       == ''
        assert str(req.caller_ip)      == ''
        assert req.max_hours           == 1
        assert str(req.admin_password) == ''

    def test__round_trip_via_json(self):
        original = Schema__OS__Stack__Create__Request(stack_name='os-quiet-fermi', region='eu-west-2',
                                                       instance_type='m6i.large',
                                                       caller_ip='1.2.3.4',
                                                       max_hours=4,
                                                       admin_password='AAAA-BBBB-1234-cdef')
        again = Schema__OS__Stack__Create__Request.from_json(original.json())
        assert str(again.stack_name)     == 'os-quiet-fermi'
        assert str(again.region)         == 'eu-west-2'
        assert str(again.instance_type)  == 'm6i.large'                              # Dot preserved
        assert str(again.caller_ip)      == '1.2.3.4'                                # Dotted-quad preserved
        assert again.max_hours           == 4
        assert str(again.admin_password) == 'AAAA-BBBB-1234-cdef'
