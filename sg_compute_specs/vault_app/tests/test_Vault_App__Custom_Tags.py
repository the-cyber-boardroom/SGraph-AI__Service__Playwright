# ═══════════════════════════════════════════════════════════════════════════════
# Tests — --tag KEY=VALUE (operator-supplied EC2 tags)
# Custom tags merge into the instance tag set; reserved stack keys are rejected
# (before any AWS call); the name-prefix duplication also covers them.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.vault_app.cli                       import Cli__Vault_App as cli
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service


class TestParseCustomTags:

    def test_parses_lines_into_dict(self):
        svc = Vault_App__Service()
        out = svc.parse_custom_tags('Project=akeia\nCostCenter=42')
        assert out == {'Project': 'akeia', 'CostCenter': '42'}

    def test_blank_is_empty(self):
        assert Vault_App__Service().parse_custom_tags('') == {}

    def test_value_may_contain_equals(self):
        out = Vault_App__Service().parse_custom_tags('Note=a=b=c')
        assert out == {'Note': 'a=b=c'}

    @pytest.mark.parametrize('reserved', ['Name', 'StackName', 'StackType', 'Purpose',
                                          'AccessToken', 'StackEngine', 'Namespace'])
    def test_reserved_keys_rejected(self, reserved):
        with pytest.raises(ValueError, match='reserved'):
            Vault_App__Service().parse_custom_tags(f'{reserved}=whatever')


class TestCliTagWiring:

    def test_set_extras_joins_tags(self):
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, tag=['Project=akeia', 'CostCenter=42'])
        assert str(req.custom_tags) == 'Project=akeia\nCostCenter=42'

    def test_missing_equals_raises(self):
        req = Schema__Vault_App__Create__Request()
        with pytest.raises(Exception, match='KEY=VALUE'):
            cli._set_extras(req, tag=['NOTKV'])

    def test_empty_key_raises(self):
        req = Schema__Vault_App__Create__Request()
        with pytest.raises(Exception, match='KEY=VALUE'):
            cli._set_extras(req, tag=['=novalue'])

    def test_default_is_empty(self):
        assert str(Schema__Vault_App__Create__Request().custom_tags) == ''


class TestCustomTagsInTagList:
    # End-to-end of the tag-list assembly the service does (build → merge → prefix),
    # without AWS: custom tags land as real tags and survive name-prefix duplication.

    def _tags_with(self, custom: dict, name_prefix=''):
        from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder       import EC2__Tags__Builder
        from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper import STACK_TYPE
        extra = {'StackEngine': 'docker'}
        extra.update(custom)
        tags = EC2__Tags__Builder(stack_type=STACK_TYPE).build('warm-bohr', '1.2.3.4/32', 'tester',
                                                               extra_tags=extra)
        return Vault_App__Service().apply_name_prefix(tags, 'warm-bohr', name_prefix)

    def test_custom_tag_present(self):
        tags = self._tags_with({'Project': 'akeia'})
        assert {'Key': 'Project', 'Value': 'akeia'} in tags

    def test_custom_tag_gets_prefixed_duplicate(self):
        tags = self._tags_with({'Project': 'akeia'}, name_prefix='acme')
        keys = [t['Key'] for t in tags]
        assert 'Project'      in keys
        assert 'acme-Project' in keys                          # prefixed duplicate from apply_name_prefix
