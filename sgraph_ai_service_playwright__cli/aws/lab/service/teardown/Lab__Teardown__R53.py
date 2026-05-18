# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Teardown__R53
# Delete a Route 53 record entry from the lab ledger.
# Re-reads the record before deleting (idempotency: skip if already gone).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client            import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type        import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry      import Schema__Lab__Ledger__Entry


class Lab__Teardown__R53(Type_Safe):
    r53 : Route53__AWS__Client                                                     # injected; allows in-memory fake in tests

    def setup(self) -> 'Lab__Teardown__R53':
        if self.r53 is None:
            self.r53 = Route53__AWS__Client()
        return self

    def teardown(self, entry: Schema__Lab__Ledger__Entry) -> bool:
        resource_id = str(entry.resource_id)
        # resource_id format: zone_id/name/type  (set by the experiment)
        parts       = resource_id.split('/')
        if len(parts) < 3:
            return False                                                            # unrecognised resource_id format → skip
        zone_id     = parts[0]
        name        = parts[1]
        record_type_str = parts[2].upper()

        try:
            rtype = Enum__Route53__Record_Type(record_type_str)
        except ValueError:
            return False

        try:
            existing = self.r53.get_record(zone_id, name, rtype)
        except Exception:
            return False

        if existing is None:
            return True                                                            # already deleted — idempotent

        try:
            self.r53.delete_record(zone_id, name, rtype)
            return True
        except Exception:
            return False
