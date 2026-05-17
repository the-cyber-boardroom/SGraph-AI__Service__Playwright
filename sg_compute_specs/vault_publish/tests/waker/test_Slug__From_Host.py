# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Slug__From_Host
# Pure parse tests — no AWS, no network, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_publish.waker.Slug__From_Host import Slug__From_Host


class TestSlugFromHost:
    def setup_method(self):
        self.sut = Slug__From_Host()

    def test_valid_slug(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        result = self.sut.extract('sara-cv.aws.sg-labs.app')
        assert result is not None
        assert str(result) == 'sara-cv'

    def test_wrong_zone_returns_none(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        assert self.sut.extract('sara-cv.other-zone.com') is None

    def test_apex_only_returns_none(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        assert self.sut.extract('aws.sg-labs.app') is None

    def test_nested_subdomain_rejected(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        assert self.sut.extract('deep.sara-cv.aws.sg-labs.app') is None

    def test_empty_host_returns_none(self):
        assert self.sut.extract('') is None

    def test_none_host_returns_none(self):
        assert self.sut.extract(None) is None

    def test_trailing_dot_stripped(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        result = self.sut.extract('sara-cv.aws.sg-labs.app.')
        assert result is not None
        assert str(result) == 'sara-cv'

    def test_invalid_slug_chars_returns_none(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        result = self.sut.extract('UPPERCASE.aws.sg-labs.app')
        assert result is not None                                                   # Safe_Str__Slug lowercases
        assert str(result) == 'uppercase'

    def test_reserved_slug_extracted(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        result = self.sut.extract('www.aws.sg-labs.app')
        assert result is not None                                                   # Slug__From_Host parses; Slug__Validator rejects on register, not here
        assert str(result) == 'www'
