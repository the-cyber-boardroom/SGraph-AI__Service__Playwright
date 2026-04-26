# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — sp el forward helpers
# Pins the testable pieces of `sp el forward`: the service→port mapping and
# the AWS CLI arg-list builder.  The actual subprocess call is opaque — same
# as cmd_connect / cmd_exec, those aren't unit-tested either.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from scripts.elastic                                                                import (
    FORWARD_SERVICE_PORTS,
    build_forward_command,
    remote_port_for_service,
)


class test_remote_port_for_service(TestCase):

    def test_three_known_services(self):
        assert remote_port_for_service('kibana')  == 5601
        assert remote_port_for_service('elastic') == 9200
        assert remote_port_for_service('nginx')   == 443

    def test_case_insensitive(self):                                                # KIBANA / Kibana / kibana all resolve
        assert remote_port_for_service('KIBANA') == 5601
        assert remote_port_for_service('Elastic') == 9200

    def test_strips_whitespace(self):
        assert remote_port_for_service('  kibana  ') == 5601

    def test_unknown_service_raises_value_error(self):
        try:
            remote_port_for_service('foo')
            assert False, 'expected ValueError'
        except ValueError as exc:
            assert "'foo'" in str(exc)
            assert 'kibana' in str(exc)                                              # Error message lists the valid options

    def test_empty_service_raises(self):
        try:
            remote_port_for_service('')
            assert False, 'expected ValueError'
        except ValueError:
            pass

    def test_service_ports_dict_has_exactly_three_entries(self):                    # Locks the surface — adding a new service is a deliberate change here
        assert set(FORWARD_SERVICE_PORTS.keys()) == {'kibana', 'elastic', 'nginx'}


class test_build_forward_command(TestCase):

    def test_basic_command_no_region(self):
        args = build_forward_command(instance_id='i-0abc', remote_port=5601, local_port=5601)
        assert args == ['aws', 'ssm', 'start-session',
                        '--target'       , 'i-0abc'                          ,
                        '--document-name', 'AWS-StartPortForwardingSession'  ,
                        '--parameters'   , 'portNumber=5601,localPortNumber=5601']

    def test_region_appended_when_set(self):
        args = build_forward_command(instance_id='i-0abc', remote_port=9200, local_port=9201, region='eu-west-2')
        assert args[-2:] == ['--region', 'eu-west-2']

    def test_region_omitted_when_empty(self):
        args = build_forward_command(instance_id='i-0abc', remote_port=443, local_port=8443, region='')
        assert '--region' not in args

    def test_local_port_can_differ_from_remote(self):                               # User can map remote 443 to local 8443 to avoid sudo
        args = build_forward_command(instance_id='i-0abc', remote_port=443, local_port=8443)
        params = args[args.index('--parameters') + 1]
        assert params == 'portNumber=443,localPortNumber=8443'

    def test_target_carries_instance_id(self):                                      # The first positional after --target must be the EC2 instance id
        args = build_forward_command(instance_id='i-0deadbeef', remote_port=5601, local_port=5601)
        target_idx = args.index('--target')
        assert args[target_idx + 1] == 'i-0deadbeef'

    def test_document_name_is_port_forwarding(self):                                # AWS-StartPortForwardingSession is the AWS-managed document; AWS-StartSSHSession or AWS-StartInteractiveCommand would be wrong
        args = build_forward_command(instance_id='i-0abc', remote_port=5601, local_port=5601)
        doc_idx = args.index('--document-name')
        assert args[doc_idx + 1] == 'AWS-StartPortForwardingSession'

    def test_int_coercion_on_ports(self):                                           # Defensive: even if a caller passes string-shaped numbers, we coerce
        args = build_forward_command(instance_id='i-0abc', remote_port='5601', local_port='5601')
        params = args[args.index('--parameters') + 1]
        assert params == 'portNumber=5601,localPortNumber=5601'
