# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Enum__S3__Storage_Class
# Pins the eleven AWS storage class members + UNKNOWN, and the str-roundtrip
# behaviour Type_Safe relies on for JSON serialisation.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__S3__Storage_Class import Enum__S3__Storage_Class


class test_Enum__S3__Storage_Class(TestCase):

    def test_known_members(self):                                                   # The set of values matches AWS's StorageClass enum (plus UNKNOWN)
        names = {m.name for m in Enum__S3__Storage_Class}
        assert 'STANDARD'            in names
        assert 'STANDARD_IA'         in names
        assert 'GLACIER'             in names
        assert 'DEEP_ARCHIVE'        in names
        assert 'INTELLIGENT_TIERING' in names
        assert 'UNKNOWN'             in names

    def test_str_returns_value(self):                                               # Type_Safe .json() relies on str(member) returning the wire value
        assert str(Enum__S3__Storage_Class.STANDARD)    == 'STANDARD'
        assert str(Enum__S3__Storage_Class.STANDARD_IA) == 'STANDARD_IA'
        assert str(Enum__S3__Storage_Class.UNKNOWN)     == 'UNKNOWN'

    def test_lookup_by_value(self):                                                 # Round-trip from wire string back to member
        assert Enum__S3__Storage_Class('STANDARD') == Enum__S3__Storage_Class.STANDARD
        assert Enum__S3__Storage_Class('GLACIER')  == Enum__S3__Storage_Class.GLACIER
