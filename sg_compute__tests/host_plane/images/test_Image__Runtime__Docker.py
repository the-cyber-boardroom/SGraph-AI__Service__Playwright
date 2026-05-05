# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Image__Runtime__Docker
# Exercises the docker CLI adapter; skipped if docker is not in PATH.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import pytest
from unittest import TestCase

from sg_compute.host_plane.images.schemas.Schema__Image__Info             import Schema__Image__Info
from sg_compute.host_plane.images.schemas.Schema__Image__List             import Schema__Image__List
from sg_compute.host_plane.images.schemas.Schema__Image__Load__Response   import Schema__Image__Load__Response
from sg_compute.host_plane.images.schemas.Schema__Image__Remove__Response import Schema__Image__Remove__Response
from sg_compute.host_plane.images.service.Image__Runtime__Docker          import Image__Runtime__Docker

pytestmark = pytest.mark.skipif(not shutil.which('docker'),
                                 reason='docker not in PATH')


class test_Image__Runtime__Docker(TestCase):

    def setUp(self):
        self.runtime = Image__Runtime__Docker()

    def test_list__returns_schema(self):
        result = self.runtime.list()
        assert isinstance(result, Schema__Image__List)
        assert isinstance(result.images, list)
        assert result.count == len(result.images)

    def test_list__each_item_has_required_fields(self):
        result = self.runtime.list()
        for img in result.images:
            assert isinstance(img, Schema__Image__Info)
            assert img.id
            assert isinstance(img.tags, list)
            assert img.size_mb >= 0

    def test_inspect__nonexistent__returns_none(self):
        result = self.runtime.inspect('no-such-image-xyz-test-999')
        assert result is None

    def test_load__nonexistent_path__returns_error(self):
        result = self.runtime.load('/tmp/no-such-image-for-test.tar')
        assert isinstance(result, Schema__Image__Load__Response)
        assert result.loaded is False
        assert result.error

    def test_remove__nonexistent__returns_error(self):
        result = self.runtime.remove('no-such-image-xyz-test-999:latest')
        assert isinstance(result, Schema__Image__Remove__Response)
        assert result.removed is False
        assert result.error
