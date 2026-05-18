# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Teardown__R53
# In-memory R53 client; verifies idempotency (already-gone record → True,
# no error); verifies successful teardown flow.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type     import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client         import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State        import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type       import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id   import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id     import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry   import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__R53  import Lab__Teardown__R53


class _Fake_Route53__AWS__Client(Route53__AWS__Client):
    _existing_records: dict = None
    _deleted: list = None

    def __init__(self):
        super().__init__()
        self._existing_records = {}
        self._deleted          = []

    def setup(self, **kwargs) -> '_Fake_Route53__AWS__Client':
        return self

    def add_record(self, zone_id: str, name: str, rtype: str) -> None:
        self._existing_records[(zone_id, name, rtype.upper())] = True

    def get_record(self, zone_id: str, name: str, record_type: Enum__Route53__Record_Type):
        from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Record import Schema__Route53__Record
        key = (zone_id, name, str(record_type).upper())
        if key in self._existing_records:
            rec = Schema__Route53__Record()
            return rec
        return None

    def delete_record(self, zone_id_or_name: str, name: str, record_type: Enum__Route53__Record_Type,
                      values=None, ttl=None):
        key = (zone_id_or_name, name, str(record_type).upper())
        self._existing_records.pop(key, None)
        self._deleted.append((zone_id_or_name, name, str(record_type)))
        from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Change__Result import Schema__Route53__Change__Result
        return Schema__Route53__Change__Result()


def _make_entry(resource_id: str) -> Schema__Lab__Ledger__Entry:
    return Schema__Lab__Ledger__Entry(
        entry_id      = Safe_Str__Lab__Entry_Id('a' * 32),
        run_id        = Safe_Str__Lab__Run_Id('2026-05-18T00:00:00Z__abc123'),
        resource_type = Enum__Lab__Resource_Type.R53_RECORD,
        resource_id   = Safe_Str__AWS__ARN(resource_id),
        region        = Safe_Str__AWS__Region('us-east-1'),
        created_at    = '2026-05-18T00:00:00Z',
        expires_at    = '2026-05-18T01:00:00Z',
        state         = Enum__Lab__Entry__State.PENDING,
        experiment    = 'test',
        extra         = '',
    )


class test_Lab__Teardown__R53(TestCase):

    def setUp(self):
        self.fake_r53 = _Fake_Route53__AWS__Client()
        self.teardown = Lab__Teardown__R53(r53=self.fake_r53)

    def test_1__teardown_existing_record_returns_true(self):
        self.fake_r53.add_record('ZONE1', 'test.example.com', 'A')
        entry  = _make_entry('ZONE1/test.example.com/A')
        result = self.teardown.teardown(entry)
        assert result is True
        assert ('ZONE1', 'test.example.com', 'A') in self.fake_r53._deleted

    def test_2__teardown_already_gone_record_is_idempotent(self):
        entry  = _make_entry('ZONE1/already-gone.example.com/A')
        result = self.teardown.teardown(entry)
        assert result is True                                                       # already gone → True, no error
        assert self.fake_r53._deleted == []                                        # no delete call made

    def test_3__malformed_resource_id_returns_false(self):
        entry  = _make_entry('INVALID_NO_SLASHES')
        result = self.teardown.teardown(entry)
        assert result is False

    def test_4__unknown_record_type_returns_false(self):
        entry  = _make_entry('ZONE1/test.example.com/BADTYPE')
        result = self.teardown.teardown(entry)
        assert result is False

    def test_5__teardown_cname_record(self):
        self.fake_r53.add_record('ZONE2', 'www.example.com', 'CNAME')
        entry  = _make_entry('ZONE2/www.example.com/CNAME')
        result = self.teardown.teardown(entry)
        assert result is True
