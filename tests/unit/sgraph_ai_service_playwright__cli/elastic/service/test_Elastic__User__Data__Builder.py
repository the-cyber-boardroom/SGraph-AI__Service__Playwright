# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__User__Data__Builder
# Pure-string assertions on the rendered cloud-init script.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder, ELASTIC_VERSION, KIBANA_VERSION


STACK_NAME = 'elastic-happy-turing'
PASSWORD   = 'abcDEF123456_-secret'


class test_Elastic__User__Data__Builder(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.builder  = Elastic__User__Data__Builder()
        cls.rendered = cls.builder.render(stack_name       = Safe_Str__Elastic__Stack__Name(STACK_NAME),
                                          elastic_password = Safe_Str__Elastic__Password   (PASSWORD  ))

    def test_starts_with_shebang(self):
        assert self.rendered.startswith('#!/bin/bash')

    def test_contains_stack_name(self):
        assert STACK_NAME in self.rendered

    def test_contains_password_in_env_file(self):                                   # Password lands in the env-file heredoc only
        assert f'ELASTIC_PASSWORD={PASSWORD}' in self.rendered

    def test_contains_pinned_image_versions(self):
        assert f'docker.elastic.co/elasticsearch/elasticsearch:{ELASTIC_VERSION}' in self.rendered
        assert f'docker.elastic.co/kibana/kibana:{KIBANA_VERSION}'                in self.rendered

    def test_contains_nginx_path_routing(self):                                     # /_elastic/ → ES; / → Kibana
        assert 'location /_elastic/' in self.rendered
        assert 'proxy_pass http://elasticsearch'  in self.rendered
        assert 'proxy_pass http://kibana'          in self.rendered

    def test_publishes_only_443(self):                                              # Kibana 5601 + ES 9200 stay 127.0.0.1-bound
        assert '"443:443"' in self.rendered
        assert '"127.0.0.1:5601:5601"' in self.rendered
        assert '"127.0.0.1:9200:9200"' in self.rendered

    def test_self_signed_cert_step(self):
        assert 'openssl req -x509' in self.rendered
        assert 'tls.crt' in self.rendered
        assert 'tls.key' in self.rendered

    def test_password_is_chmod_600(self):
        assert 'chmod 600 /opt/sg-elastic/.env' in self.rendered

    def test_xpack_security_enabled(self):                                          # Brief requires basic-auth on the elastic user
        assert 'xpack.security.enabled=true' in self.rendered

    def test_schedules_delayed_ssm_agent_restart(self):                             # Without this, the SSM agent gets stuck in credential-failure backoff
        # Regression: the agent boots before IAM has propagated our just-created
        # role. A scheduled restart 90s into boot gives IAM time to settle and
        # the agent re-reads instance metadata. Pin the systemd-run line so it
        # can't get accidentally removed.
        assert 'systemd-run --on-active=90'    in self.rendered
        assert 'sg-elastic-ssm-restart'        in self.rendered
        assert 'systemctl restart amazon-ssm-agent' in self.rendered
