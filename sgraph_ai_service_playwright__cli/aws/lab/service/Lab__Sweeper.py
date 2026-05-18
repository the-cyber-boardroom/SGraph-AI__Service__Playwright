# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Sweeper
# Tag-driven leak sweeper. Scans AWS for resources tagged sg:lab=true with
# sg:lab:run-id + sg:lab:expires-at and optionally deletes them. Only the
# R53 scanner is fully implemented in Foundation; all others stub out.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from typing   import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State          import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type         import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Sweep__Report     import Schema__Lab__Sweep__Report
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                    import Lab__Ledger
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Dispatcher import Lab__Teardown__Dispatcher

_REQUIRED_TAGS = {'sg:lab', 'sg:lab:run-id', 'sg:lab:expires-at'}


class Lab__Sweeper(Type_Safe):
    ledger     : Lab__Ledger
    dispatcher : Lab__Teardown__Dispatcher

    def setup(self) -> 'Lab__Sweeper':
        if not self.ledger.ledger_path:
            self.ledger.setup()
        return self

    def sweep(self,
              apply       : bool = False,
              older_than  : Optional[str] = None) -> Schema__Lab__Sweep__Report:
        report   = Schema__Lab__Sweep__Report(dry_run=not apply)
        entries  = self.ledger.pending_entries()
        now      = datetime.now(timezone.utc)
        report.scanned = len(entries)

        for entry in entries:
            if not self._has_required_tags(entry):
                continue
            if not self._is_expired(entry, now, older_than):
                continue
            report.leaked += 1
            report.resources.append(entry)
            if apply:
                try:
                    self.dispatcher.teardown(entry)
                    self.ledger.update_state(str(entry.entry_id), Enum__Lab__Entry__State.DELETED)
                    report.deleted += 1
                except Exception:
                    pass                                                            # log on best-effort; don't abort sweep

        return report

    # ── private ───────────────────────────────────────────────────────────────

    def _has_required_tags(self, entry) -> bool:
        return entry.resource_type is not None                                     # foundation: trust that entries written by lab always carry tags

    def _is_expired(self, entry, now: datetime, older_than: Optional[str]) -> bool:
        expires_at_str = entry.expires_at
        if not expires_at_str:
            return True                                                            # no TTL → treat as expired
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if older_than:
                cutoff = self._parse_older_than(older_than, now)
                return now > cutoff
            return now > expires_at
        except ValueError:
            return True                                                            # unparseable → treat as expired

    def _parse_older_than(self, spec: str, now: datetime) -> datetime:
        from datetime import timedelta
        spec = spec.strip().lower()
        if spec.endswith('h'):
            return now - timedelta(hours=float(spec[:-1]))
        if spec.endswith('m'):
            return now - timedelta(minutes=float(spec[:-1]))
        if spec.endswith('d'):
            return now - timedelta(days=float(spec[:-1]))
        return now                                                                 # unknown spec → not expired
