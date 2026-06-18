# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: committed-compose drift guard
# The committed local docker/compose/docker-compose.yml must equal the template
# render (default images). Keeps the `docker compose up` file honest.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path
from unittest                                                                       import TestCase

import sg_compute_specs.content_proxy                                               as content_proxy_pkg
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import Content_Proxy__Compose__Template


class test_compose_committed_no_drift(TestCase):

    def test_committed_compose_matches_template(self):
        pkg_dir   = Path(content_proxy_pkg.__file__).parent
        committed = (pkg_dir / 'docker' / 'compose' / 'docker-compose.yml').read_text()
        rendered  = Content_Proxy__Compose__Template().render()
        assert committed == rendered, ('committed docker-compose.yml drifted from the template — '
                                       'regenerate it from Content_Proxy__Compose__Template().render()')
