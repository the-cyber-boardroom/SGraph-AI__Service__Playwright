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

    def test_kibana_uses_service_account_token_not_elastic_superuser(self):
        # Regression: Kibana 8.13 refuses ELASTICSEARCH_USERNAME=elastic with
        # exit 78 ("value of 'elastic' is forbidden"). Must use a service
        # account token minted from ES after it's up.
        assert 'ELASTICSEARCH_SERVICEACCOUNTTOKEN=${KIBANA_SERVICE_TOKEN}' in self.rendered
        # Match only the docker-compose env-var list syntax ("- KEY=VAL"), not explanatory comments
        assert '- ELASTICSEARCH_USERNAME=' not in self.rendered
        assert '- ELASTICSEARCH_PASSWORD=' not in self.rendered

    def test_encryption_keys_set_for_kibana(self):                                  # Kibana 8.10+ hard-fails boot if encryptedSavedObjects key is missing
        for var in ('XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY',
                    'XPACK_SECURITY_ENCRYPTIONKEY'             ,
                    'XPACK_REPORTING_ENCRYPTIONKEY'            ):
            assert f'{var}=${{KIBANA_ENCRYPTION_KEY}}' in self.rendered
        assert 'KIBANA_ENCRYPTION_KEY=$(openssl rand -hex 32)' in self.rendered     # Generated at boot, written to .env

    def test_staged_boot_sequence(self):                                            # ES first, then token mint, then Kibana + nginx — order matters
        es_up        = self.rendered.find('up -d elasticsearch')
        token_create = self.rendered.find('bin/elasticsearch-service-tokens create elastic/kibana')
        kibana_up    = self.rendered.find('up -d kibana nginx')
        assert es_up        >= 0
        assert token_create >  es_up
        assert kibana_up    >  token_create
