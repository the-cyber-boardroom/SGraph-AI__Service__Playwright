# ═══════════════════════════════════════════════════════════════════════════════
# Tests — S3 Primitives
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sgraph_ai_service_playwright.schemas.primitives.s3 import (
    Safe_Str__S3_Key                                                     ,
    Safe_Str__S3_Bucket                                                  ,
)


class test_Safe_Str__S3_Key(TestCase):

    def test__accepts_nested_path(self):
        key = 'captures/2026/04/session-abc/screenshot-001.png'
        assert str(Safe_Str__S3_Key(key)) == key

    def test__replaces_disallowed_chars(self):
        assert str(Safe_Str__S3_Key('bad key!')) == 'bad_key_'


class test_Safe_Str__S3_Bucket(TestCase):

    def test__accepts_lowercase_bucket(self):
        assert str(Safe_Str__S3_Bucket('my-bucket-123')) == 'my-bucket-123'
        assert str(Safe_Str__S3_Bucket('sgraph.prod'  )) == 'sgraph.prod'

    def test__rejects_uppercase(self):                                              # MATCH mode + strict_validation → ValueError
        with pytest.raises(ValueError):
            Safe_Str__S3_Bucket('MyBucket')

    def test__rejects_leading_hyphen(self):
        with pytest.raises(ValueError):
            Safe_Str__S3_Bucket('-leading-hyphen')

    def test__rejects_trailing_hyphen(self):
        with pytest.raises(ValueError):
            Safe_Str__S3_Bucket('trailing-')
