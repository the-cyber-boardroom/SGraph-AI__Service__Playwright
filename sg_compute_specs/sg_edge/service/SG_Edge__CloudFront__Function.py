# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: SG_Edge__CloudFront__Function
# Loads the bundled CloudFront viewer-request function source (preserves the
# viewer Host and extracts the slug into X-SG-Host / X-SG-Slug headers the proxy
# reads). Slice 5's Setup__CF publishes this via the existing
# CloudFront__Function__AWS__Client (create / publish / attach). Kept as a tiny
# loader so the JS lives in one place and co-evolves with the proxy.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

FUNCTION_SOURCE_PATH = os.path.join(os.path.dirname(__file__), '..', 'cloudfront_function', 'viewer_request.js')
DEFAULT_FUNCTION_NAME = 'sg-edge-viewer-request'


class SG_Edge__CloudFront__Function(Type_Safe):
    name : str = DEFAULT_FUNCTION_NAME

    def source(self) -> str:                                                         # the CloudFront Functions JS to publish
        with open(os.path.abspath(FUNCTION_SOURCE_PATH)) as f:
            return f.read()
