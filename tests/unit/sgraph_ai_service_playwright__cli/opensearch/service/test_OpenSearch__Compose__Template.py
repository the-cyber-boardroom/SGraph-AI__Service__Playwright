# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__Compose__Template
# Locks the placeholder contract + the canonical service / network / volume
# names so future expansion lands as a reviewable diff.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Compose__Template import (COMPOSE_TEMPLATE       ,
                                                                                                   DASHBOARDS_IMAGE       ,
                                                                                                   OS_IMAGE               ,
                                                                                                   PLACEHOLDERS           ,
                                                                                                   OpenSearch__Compose__Template)


class test_OpenSearch__Compose__Template(TestCase):

    def setUp(self):
        self.tpl = OpenSearch__Compose__Template()

    def test_render__substitutes_all_placeholders(self):
        out = self.tpl.render(admin_password='AAAA-BBBB-1234-cdef')
        assert OS_IMAGE                       in out
        assert DASHBOARDS_IMAGE               in out
        assert 'OPENSEARCH_INITIAL_ADMIN_PASSWORD=AAAA-BBBB-1234-cdef' in out
        assert '-Xms2g -Xmx2g'                in out                                # Default heap

    def test_render__custom_heap(self):
        out = self.tpl.render(admin_password='secret-1234567890ab', heap_size='4g')
        assert '-Xms4g -Xmx4g' in out

    def test_render__custom_images(self):                                           # Tests can pin a known version even though prod uses :latest
        out = self.tpl.render(admin_password='secret-1234567890ab',
                              os_image='opensearchproject/opensearch:2.13.0',
                              dashboards_image='opensearchproject/opensearch-dashboards:2.13.0')
        assert 'opensearch:2.13.0'             in out
        assert 'opensearch-dashboards:2.13.0'  in out

    def test_render__no_placeholders_leaked(self):                                  # Defensive: every {key} must be substituted
        out      = self.tpl.render(admin_password='secret-1234567890ab')
        leftover = re.findall(r'\{([a-z_]+)\}', out)
        assert leftover == []

    def test_render__includes_canonical_container_names(self):                      # sp os exec / connect target these
        out = self.tpl.render(admin_password='secret-1234567890ab')
        assert 'container_name: sg-opensearch'             in out
        assert 'container_name: sg-opensearch-dashboards'  in out

    def test_render__shared_network_named_sg_net(self):                             # Same convention as the playwright stack
        out = self.tpl.render(admin_password='secret-1234567890ab')
        assert '- sg-net' in out                                                    # service belongs to network
        assert 'sg-net:'  in out                                                    # network defined

    def test_render__memory_lock_enabled(self):                                     # Required for OpenSearch 2.x — JVM heap must be unswappable
        out = self.tpl.render(admin_password='secret-1234567890ab')
        assert 'bootstrap.memory_lock=true' in out
        assert 'memlock:'                   in out

    def test_render__dashboards_depends_on_opensearch(self):                        # Dashboards crashes immediately if OS isn't reachable on boot
        out = self.tpl.render(admin_password='secret-1234567890ab')
        assert 'depends_on:'   in out
        assert '- opensearch'  in out                                               # the dependency entry

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', COMPOSE_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)
