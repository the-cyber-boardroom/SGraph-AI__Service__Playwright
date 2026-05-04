# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Image__Build__Service
# Stage-only tests run with no Docker daemon required. The Docker invocation
# itself is exercised by the existing tests/docker/ deploy-via-pytest tests
# which gate on Docker + AWS creds. The build() method is also tested here
# with a real-implementation in-memory docker client (a fake whose
# images.build() records args + returns an in-memory image stub).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Request   import Schema__Image__Build__Request
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item      import Schema__Image__Stage__Item
from sgraph_ai_service_playwright__cli.image.service.Image__Build__Service           import (DEFAULT_IGNORE_NAMES                ,
                                                                                              Image__Build__Service               )


class _Fake_Docker_Image:                                                           # In-memory stand-in for docker SDK Image — not a mock; a real class
    def __init__(self, image_id, tags):
        self.id   = image_id
        self.tags = list(tags)


class _Fake_Docker_Images:                                                          # In-memory stand-in for docker SDK images endpoint
    def __init__(self, response_image):
        self.calls          = []
        self.response_image = response_image
    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.response_image, ['fake-build-log-line']


class _Fake_Docker_Client:
    def __init__(self, response_image):
        self.images = _Fake_Docker_Images(response_image)


class test_Image__Build__Service(TestCase):

    def setUp(self):
        self.service       = Image__Build__Service()
        self.work_dir      = tempfile.mkdtemp(prefix='img_build_test_')
        self.image_folder  = os.path.join(self.work_dir, 'image-folder')
        self.build_context = os.path.join(self.work_dir, 'build-context')
        os.makedirs(self.image_folder)
        os.makedirs(self.build_context)
        with open(os.path.join(self.image_folder, 'dockerfile')        , 'w') as f: f.write('FROM scratch\nCOPY . /\n')
        with open(os.path.join(self.image_folder, 'requirements.txt')  , 'w') as f: f.write('fastapi\n')

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _make_pkg(self, root, name, files=('module.py',)):                          # Helper: build a small fake package with optional pycache noise
        pkg = os.path.join(root, name)
        os.makedirs(pkg)
        os.makedirs(os.path.join(pkg, '__pycache__'))
        for fname in files:
            with open(os.path.join(pkg, fname), 'w') as f: f.write('# fake\n')
        with open(os.path.join(pkg, '__pycache__', 'module.cpython-312.pyc'), 'wb') as f: f.write(b'\x00')
        return pkg

    # ──────────────────────────────── stage_build_context ─────────────────────────

    def test_stage_build_context__copies_dockerfile_and_requirements(self):
        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[])
        self.service.stage_build_context(request, self.build_context)

        assert os.path.isfile(os.path.join(self.build_context, 'dockerfile'))
        assert os.path.isfile(os.path.join(self.build_context, 'requirements.txt'))

    def test_stage_build_context__copies_single_file_item(self):
        loose_file = os.path.join(self.work_dir, 'lambda_entry.py')
        with open(loose_file, 'w') as f: f.write('# boot shim\n')

        item    = Schema__Image__Stage__Item(source_path=loose_file, target_name='lambda_entry.py', is_tree=False)
        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[item])
        self.service.stage_build_context(request, self.build_context)

        with open(os.path.join(self.build_context, 'lambda_entry.py')) as f:
            assert f.read() == '# boot shim\n'

    def test_stage_build_context__copies_tree_and_filters_default_noise(self):
        pkg     = self._make_pkg(self.work_dir, 'fake_pkg')
        item    = Schema__Image__Stage__Item(source_path=pkg, target_name='fake_pkg', is_tree=True)
        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[item])
        self.service.stage_build_context(request, self.build_context)

        staged = os.path.join(self.build_context, 'fake_pkg')
        assert os.path.isfile(os.path.join(staged, 'module.py'))
        assert not os.path.isdir(os.path.join(staged, '__pycache__'))               # Default ignore filtered the cache out
        assert all(not n.endswith('.pyc') for n in os.listdir(staged))              # Defensive: no pyc files in the staged tree root

    def test_stage_build_context__honours_extra_ignore_names_per_item(self):
        pkg = self._make_pkg(self.work_dir, 'pkg_with_extras')
        os.makedirs(os.path.join(pkg, 'images'))                                    # Mirrors Docker__SP__CLI's "filter the deploy/images/ folder" case
        with open(os.path.join(pkg, 'images', 'README.md'), 'w') as f: f.write('hi')

        item    = Schema__Image__Stage__Item(source_path=pkg, target_name='pkg_with_extras', is_tree=True,
                                              extra_ignore_names=['images'])
        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[item])
        self.service.stage_build_context(request, self.build_context)

        staged = os.path.join(self.build_context, 'pkg_with_extras')
        assert os.path.isfile(os.path.join(staged, 'module.py'))
        assert not os.path.isdir(os.path.join(staged, 'images'))                    # Filtered by extra_ignore_names

    def test_stage_build_context__custom_dockerfile_and_requirements_names(self):
        with open(os.path.join(self.image_folder, 'Dockerfile.alt'), 'w') as f: f.write('FROM scratch\n')
        with open(os.path.join(self.image_folder, 'reqs.txt')      , 'w') as f: f.write('typer\n')
        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[],
                                                dockerfile_name='Dockerfile.alt', requirements_name='reqs.txt')
        self.service.stage_build_context(request, self.build_context)

        assert os.path.isfile(os.path.join(self.build_context, 'Dockerfile.alt'))
        assert os.path.isfile(os.path.join(self.build_context, 'reqs.txt'))

    # ──────────────────────────────── build ───────────────────────────────────────

    def test_build__returns_typed_result_and_calls_docker_with_correct_args(self):
        loose_file = os.path.join(self.work_dir, 'extra.txt')
        with open(loose_file, 'w') as f: f.write('hi')
        item    = Schema__Image__Stage__Item(source_path=loose_file, target_name='extra.txt')

        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='ecr/img:latest', stage_items=[item])
        fake    = _Fake_Docker_Client(_Fake_Docker_Image('sha256:abc', ['ecr/img:latest']))

        result  = self.service.build(request, fake)

        assert str(result.image_id)    == 'sha256:abc'
        assert list(result.image_tags) == ['ecr/img:latest']
        assert result.duration_ms      >= 0                                         # Wall-clock; might round to 0 in fast unit-test runs
        assert len(fake.images.calls)  == 1
        call = fake.images.calls[0]
        assert call['tag']             == 'ecr/img:latest'
        assert call['dockerfile']      == 'dockerfile'
        assert call['rm']              is True
        assert os.path.basename(call['path']).startswith('sg_image_build_')         # tempdir prefix from request

    def test_build__cleans_up_tempdir_even_when_docker_raises(self):
        class _Boom_Images:
            def __init__(self): self.calls = []
            def build(self, **kw): raise RuntimeError('docker fell over')
        class _Boom_Client:
            images = _Boom_Images()

        request = Schema__Image__Build__Request(image_folder=self.image_folder, image_tag='img:latest', stage_items=[])
        before  = set(os.listdir(tempfile.gettempdir()))

        try:
            self.service.build(request, _Boom_Client())
        except RuntimeError as exc:
            assert 'docker fell over' in str(exc)

        after = set(os.listdir(tempfile.gettempdir()))
        leftover = [n for n in (after - before) if n.startswith('sg_image_build_')]
        assert leftover == []                                                       # tempdir was cleaned in the finally even though build raised

    # ──────────────────────────────── ignore callable ─────────────────────────────

    def test_make_ignore_callable__filters_defaults_and_extras(self):
        ignore = self.service.make_ignore_callable(extra_ignore_names=['images'])
        names  = ['__pycache__', '.pytest_cache', '.mypy_cache', 'foo.pyc', 'real.py', 'images', 'docs']
        result = ignore('/any/path', names)
        for noisy in DEFAULT_IGNORE_NAMES:
            assert noisy in result
        assert 'foo.pyc' in result
        assert 'images'  in result                                                  # From extras
        assert 'real.py' not in result
        assert 'docs'    not in result
