# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — SSM__Sidecar__Key
# Tests that don't require AWS credentials: path computation and class structure.
# AWS-calling methods (write/read/delete/exists) are tested structurally only —
# they are not invoked because no credentials are present in CI.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.platforms.ec2.secrets.SSM__Sidecar__Key                      import (SSM__Sidecar__Key ,
                                                                                      SSM_PATH_PREFIX   )


class test_SSM__Sidecar__Key(TestCase):

    def setUp(self):
        self.ssm = SSM__Sidecar__Key()

    # ── class structure ──────────────────────────────────────────────────────

    def test_is_type_safe_subclass(self):
        assert issubclass(SSM__Sidecar__Key, Type_Safe)

    def test_constants(self):
        assert SSM_PATH_PREFIX == '/sg-compute/nodes'

    # ── path computation (no AWS calls) ──────────────────────────────────────

    def test_path_for_simple_node_id(self):
        path = SSM__Sidecar__Key.path_for('test-node-001')
        assert path == '/sg-compute/nodes/test-node-001/sidecar-api-key'

    def test_path_for_adjective_noun_id(self):
        path = SSM__Sidecar__Key.path_for('ff-quiet-fermi-1234')
        assert path == '/sg-compute/nodes/ff-quiet-fermi-1234/sidecar-api-key'

    def test_path_for_includes_prefix(self):
        path = SSM__Sidecar__Key.path_for('any-node')
        assert path.startswith(SSM_PATH_PREFIX + '/')

    def test_path_for_ends_with_sidecar_api_key(self):
        path = SSM__Sidecar__Key.path_for('any-node')
        assert path.endswith('/sidecar-api-key')

    def test_path_for_embeds_node_id(self):
        node_id = 'docker-calm-tesla-9999'
        path    = SSM__Sidecar__Key.path_for(node_id)
        assert node_id in path

    def test_path_for_is_static_method(self):
        import inspect
        assert isinstance(inspect.getattr_static(SSM__Sidecar__Key, 'path_for'), staticmethod)

    # ── AWS-touching methods exist with correct signatures ───────────────────

    def test_write_method_exists(self):
        assert callable(getattr(self.ssm, 'write', None))

    def test_read_method_exists(self):
        assert callable(getattr(self.ssm, 'read', None))

    def test_delete_method_exists(self):
        assert callable(getattr(self.ssm, 'delete', None))

    def test_exists_method_exists(self):
        assert callable(getattr(self.ssm, 'exists', None))
