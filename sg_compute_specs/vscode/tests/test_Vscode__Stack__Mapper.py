# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Stack__Mapper tests
# Pure mapper — no AWS calls. Builds Info + the SSM-forward / session commands.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.service.Vscode__Stack__Mapper import (Vscode__Stack__Mapper ,
                                                                   EDITOR_PORT           ,
                                                                   ssm_forward_command   ,
                                                                   ssm_session_command   ,
                                                                   vscode_url_for        )


def _details(**overrides) -> dict:
    base = {
        'InstanceId'      : 'i-0abc'                         ,
        'PublicIpAddress' : '1.2.3.4'                        ,
        'PrivateIpAddress': '10.0.0.5'                       ,
        'InstanceType'    : 't3.large'                       ,
        'ImageId'         : 'ami-123'                        ,
        'State'           : {'Name': 'running'}              ,
        'SecurityGroups'  : [{'GroupId': 'sg-xyz'}]          ,
        'InstanceLifecycle': 'spot'                          ,
        'Tags'            : [{'Key': 'StackName',         'Value': 'brave-fermi'},
                             {'Key': 'StackDistribution', 'Value': 'code-server'},
                             {'Key': 'StackIngress',      'Value': 'ssm-forward'}],
    }
    base.update(overrides)
    return base


class test_Vscode__Stack__Mapper(TestCase):

    def test_to_info_ssm_forward(self):
        info = Vscode__Stack__Mapper().to_info(_details(), 'eu-west-2')
        assert info.instance_id       == 'i-0abc'
        assert info.stack_name        == 'brave-fermi'
        assert info.state             == 'running'
        assert info.public_ip         == '1.2.3.4'
        assert info.security_group_id == 'sg-xyz'
        assert info.distribution      == 'code-server'
        assert info.ingress           == 'ssm-forward'
        assert info.spot              is True
        assert info.vscode_url        == f'http://localhost:{EDITOR_PORT}'      # SSM mode → loopback url
        assert 'AWS-StartPortForwardingSession' in info.ssm_forward
        assert str(EDITOR_PORT)                 in info.ssm_forward
        assert 'i-0abc'                         in info.ssm_forward
        assert 'eu-west-2'                      in info.ssm_forward
        assert 'start-session'                  in info.ssm_session
        assert 'i-0abc'                         in info.ssm_session

    def test_public_https_url_uses_public_ip(self):
        info = Vscode__Stack__Mapper().to_info(
            _details(Tags=[{'Key': 'StackName',    'Value': 'calm-bohr'},
                           {'Key': 'StackIngress', 'Value': 'public-https'}]),
            'eu-west-2')
        assert info.ingress    == 'public-https'
        assert info.vscode_url == 'https://1.2.3.4'

    def test_public_https_url_prefers_fqdn(self):
        info = Vscode__Stack__Mapper().to_info(
            _details(Tags=[{'Key': 'StackName',    'Value': 'calm-bohr'},
                           {'Key': 'StackIngress', 'Value': 'public-https'},
                           {'Key': 'StackFqdn',    'Value': 'vsc.example.com'}]),
            'eu-west-2')
        assert info.fqdn       == 'vsc.example.com'
        assert info.vscode_url == 'https://vsc.example.com'             # hostname matches the LE cert SAN

    def test_command_helpers_empty_without_instance(self):
        assert ssm_forward_command('', 'eu-west-2') == ''
        assert ssm_session_command('', 'eu-west-2') == ''

    def test_vscode_url_for(self):
        assert vscode_url_for('ssm-forward',  '1.2.3.4') == f'http://localhost:{EDITOR_PORT}'
        assert vscode_url_for('public-https', '1.2.3.4') == 'https://1.2.3.4'
        assert vscode_url_for('public-https', '')        == f'http://localhost:{EDITOR_PORT}'   # no IP → loopback fallback
