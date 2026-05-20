# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for the Phase 1 proxy assets + builders
# (OpenResty user-data builder + CloudFront viewer-request function loader)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.service.SG_Edge__CloudFront__Function import SG_Edge__CloudFront__Function
from sg_compute_specs.sg_edge.service.SG_Edge__Proxy__User_Data     import SG_Edge__Proxy__User_Data, HEREDOC_MARKER


class test_SG_Edge__Proxy__User_Data(TestCase):

    def setUp(self):
        self.builder = SG_Edge__Proxy__User_Data(version='1.2.3')

    def test_nginx_conf__is_the_static_rig(self):
        conf = self.builder.nginx_conf()
        assert 'listen      80 default_server;' in conf
        assert '/_edge/health'                   in conf
        assert '/_edge/slug_seen'                in conf
        assert '$remote_addr'             not in conf            # client IP is never logged (redaction at source)

    def test_render__writes_config_and_runs_openresty(self):
        ud = self.builder.render()
        assert ud.startswith('#!/bin/bash')
        assert f"<<'{HEREDOC_MARKER}'" in ud                     # config embedded via heredoc
        assert 'docker run -d'          in ud
        assert '-p 80:80'               in ud
        assert 'EDGE_VERSION="1.2.3"'   in ud
        assert 'openresty/openresty'    in ud
        assert 'meta-data/instance-id'  in ud                    # instance id from IMDS, not an SDK call

    def test_render__embeds_the_full_nginx_conf(self):
        ud = self.builder.render()
        assert self.builder.nginx_conf() in ud


class test_SG_Edge__CloudFront__Function(TestCase):

    def setUp(self):
        self.fn = SG_Edge__CloudFront__Function()

    def test_default_name(self):
        assert self.fn.name == 'sg-edge-viewer-request'

    def test_source__extracts_slug_into_headers(self):
        src = self.fn.source()
        assert 'function handler(event)' in src
        assert 'x-sg-slug'               in src
        assert 'x-sg-host'               in src
        assert "host.split('.')[0]"      in src                  # slug = first DNS label
