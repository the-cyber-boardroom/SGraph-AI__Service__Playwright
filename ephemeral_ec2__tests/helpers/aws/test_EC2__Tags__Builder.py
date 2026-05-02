# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — EC2__Tags__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from ephemeral_ec2.helpers.aws.EC2__Tags__Builder import EC2__Tags__Builder, TAG_PURPOSE_VALUE


class test_EC2__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = EC2__Tags__Builder(stack_type='open-design')

    def _as_dict(self, tags):
        return {t['Key']: t['Value'] for t in tags}

    def test_build__standard_keys_present(self):
        tags = self._as_dict(self.builder.build('quiet-fermi', '1.2.3.4'))
        assert tags['Name']       == 'quiet-fermi'
        assert tags['Purpose']    == TAG_PURPOSE_VALUE
        assert tags['StackName']  == 'quiet-fermi'
        assert tags['StackType']  == 'open-design'
        assert tags['CallerIP']   == '1.2.3.4'
        assert tags['CreatedBy']  == 'unknown'

    def test_build__creator_set(self):
        tags = self._as_dict(self.builder.build('s', '0.0.0.0', creator='alice'))
        assert tags['CreatedBy'] == 'alice'

    def test_build__extra_tags_appended(self):
        tags = self._as_dict(
            self.builder.build('s', '0.0.0.0', extra_tags={'OllamaBaseUrl': 'http://10.0.0.1:11434/v1'}))
        assert tags['OllamaBaseUrl'] == 'http://10.0.0.1:11434/v1'

    def test_build__returns_list_of_dicts(self):
        tags = self.builder.build('n', '0.0.0.0')
        assert isinstance(tags, list)
        assert all('Key' in t and 'Value' in t for t in tags)
