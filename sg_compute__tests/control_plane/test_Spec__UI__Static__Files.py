# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec UI static-file serving (BV2.19)
# No mocks. ui_root_override injects a temp directory; no spec has a live
# ui/ folder yet so the "absent" path is tested against the real registry.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
from pathlib                                                                   import Path
from unittest                                                                  import TestCase

from fastapi.testclient                                                        import TestClient

from sg_compute.control_plane.Fast_API__Compute                               import Fast_API__Compute
from sg_compute.core.spec.Spec__UI__Resolver                                  import Spec__UI__Resolver


class test_Spec__UI__Resolver(TestCase):

    def test_ui_path_for_spec__absent_returns_none(self):
        resolver = Spec__UI__Resolver()
        assert resolver.ui_path_for_spec('ollama') is None                    # ollama has no ui/ folder

    def test_ui_path_for_spec__unknown_spec_returns_none(self):
        resolver = Spec__UI__Resolver()
        assert resolver.ui_path_for_spec('nonexistent_spec_xyz') is None

    def test_ui_path_for_spec__override_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui_dir = Path(tmp) / 'sg_compute_specs' / 'docker' / 'ui'
            ui_dir.mkdir(parents=True)
            resolver = Spec__UI__Resolver(ui_root_override=tmp)
            assert resolver.ui_path_for_spec('docker') == ui_dir

    def test_ui_path_for_spec__override_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolver = Spec__UI__Resolver(ui_root_override=tmp)
            assert resolver.ui_path_for_spec('docker') is None               # no ui/ created in tmp


class test_Spec__UI__Static__Files(TestCase):

    def test_no_mount_when_ui_folder_absent(self):
        compute = Fast_API__Compute().setup()
        client  = TestClient(compute.app())
        resp    = client.get('/api/specs/docker/ui/nonexistent.js')
        assert resp.status_code == 404

    def test_mount_activated_when_ui_folder_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_id = 'docker'
            ui_dir  = (Path(tmp) / 'sg_compute_specs' / spec_id
                       / 'ui' / 'card' / 'v0' / 'v0.1' / 'v0.1.0')
            ui_dir.mkdir(parents=True)
            (ui_dir / 'sg-compute-docker-card.js').write_text('// test')

            compute = Fast_API__Compute(ui_root_override=tmp).setup()
            client  = TestClient(compute.app())

            resp = client.get(
                f'/api/specs/{spec_id}/ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.js'
            )
            assert resp.status_code == 200
            assert '// test' in resp.text

    def test_mount_content_type_javascript(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui_dir = Path(tmp) / 'sg_compute_specs' / 'docker' / 'ui'
            ui_dir.mkdir(parents=True)
            (ui_dir / 'test.js').write_text('// js')

            compute = Fast_API__Compute(ui_root_override=tmp).setup()
            client  = TestClient(compute.app())

            resp = client.get('/api/specs/docker/ui/test.js')
            assert resp.status_code == 200
            assert 'javascript' in resp.headers.get('content-type', '')

    def test_mount_only_for_spec_with_ui_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui_dir = Path(tmp) / 'sg_compute_specs' / 'docker' / 'ui'
            ui_dir.mkdir(parents=True)
            (ui_dir / 'test.js').write_text('// js')

            compute = Fast_API__Compute(ui_root_override=tmp).setup()
            client  = TestClient(compute.app())

            assert client.get('/api/specs/docker/ui/test.js').status_code  == 200
            assert client.get('/api/specs/ollama/ui/test.js').status_code  == 404

    def test_no_cache_control_header_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui_dir = Path(tmp) / 'sg_compute_specs' / 'docker' / 'ui'
            ui_dir.mkdir(parents=True)
            (ui_dir / 'test.js').write_text('// js')

            compute = Fast_API__Compute(ui_root_override=tmp).setup()
            client  = TestClient(compute.app())

            resp = client.get('/api/specs/docker/ui/test.js')
            assert resp.status_code == 200
            assert 'cache-control' not in resp.headers                        # CloudFront owns caching
