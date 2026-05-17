# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Edit__Diff
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.edit.Edit__Diff             import Edit__Diff
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot import Schema__Edit__Snapshot, SENTINEL


def _snap(**kwargs) -> Schema__Edit__Snapshot:
    return Schema__Edit__Snapshot(**kwargs)


class test_Edit__Diff__roles(TestCase):

    def test_no_changes_produces_empty_diff(self):
        before = _snap(roles={'default': {'region': 'us-east-1',
                                          'assume_role_arn': '',
                                          'session_name': ''}})
        after  = _snap(roles={'default': {'region': 'us-east-1',
                                          'assume_role_arn': '',
                                          'session_name': ''}})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes is False
        assert diff.items == []

    def test_add_role(self):
        before = _snap(roles={})
        after  = _snap(roles={'admin': {'region': 'eu-west-1',
                                         'assume_role_arn': '',
                                         'session_name': ''}})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes
        kinds = [i.kind for i in diff.items]
        assert 'add' in kinds

    def test_remove_role(self):
        before = _snap(roles={'default': {'region': 'us-east-1',
                                           'assume_role_arn': '',
                                           'session_name': ''}})
        after  = _snap(roles={})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes
        assert any(i.kind == 'remove' and i.namespace == 'roles' for i in diff.items)

    def test_modify_region(self):
        before = _snap(roles={'default': {'region': 'us-east-1',
                                           'assume_role_arn': '',
                                           'session_name': ''}})
        after  = _snap(roles={'default': {'region': 'eu-west-2',
                                           'assume_role_arn': '',
                                           'session_name': ''}})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes
        item = diff.items[0]
        assert item.kind      == 'modify'
        assert item.namespace == 'roles'
        assert 'region' in item.key
        assert item.old_value == 'us-east-1'
        assert item.new_value == 'eu-west-2'


class test_Edit__Diff__aws_credentials(TestCase):

    def test_sentinel_in_secret_key_means_no_change(self):
        before = _snap(aws_credentials={'default': {'access_key': 'AKIAIOSFODNN7EXAMPLE',
                                                     'secret_key': 'old_secret'}})
        after  = _snap(aws_credentials={'default': {'access_key': 'AKIAIOSFODNN7EXAMPLE',
                                                     'secret_key': SENTINEL}})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes is False        # sentinel means unchanged

    def test_changed_access_key_detected(self):
        before = _snap(aws_credentials={'default': {'access_key': 'AKIAIOSFODNN7EXAMPLE',
                                                     'secret_key': SENTINEL}})
        after  = _snap(aws_credentials={'default': {'access_key': 'AKIANEWKEY1234567890',
                                                     'secret_key': SENTINEL}})
        diff = Edit__Diff().diff(before, after)
        assert diff.has_changes
        assert any('access_key' in i.key for i in diff.items)


class test_Edit__Diff__vault_keys(TestCase):

    def test_sentinel_vault_key_unchanged(self):
        before = _snap(vault_keys={'my-vault': 'super-secret'})
        after  = _snap(vault_keys={'my-vault': SENTINEL})
        diff   = Edit__Diff().diff(before, after)
        assert diff.has_changes is False

    def test_new_vault_key_is_add(self):
        before = _snap(vault_keys={})
        after  = _snap(vault_keys={'new-vault': 'new-key-value'})
        diff   = Edit__Diff().diff(before, after)
        assert diff.has_changes
        assert any(i.kind == 'add' and i.namespace == 'vault_keys' for i in diff.items)


class test_Edit__Diff__secrets(TestCase):

    def test_sentinel_secret_unchanged(self):
        before = _snap(secrets={'my-ns': {'pw': 'hunter2'}})
        after  = _snap(secrets={'my-ns': {'pw': SENTINEL}})
        diff   = Edit__Diff().diff(before, after)
        assert diff.has_changes is False

    def test_add_secret(self):
        before = _snap(secrets={})
        after  = _snap(secrets={'my-ns': {'new-pw': 'new-value'}})
        diff   = Edit__Diff().diff(before, after)
        assert diff.has_changes
        assert any(i.kind == 'add' and i.namespace == 'secrets' for i in diff.items)
