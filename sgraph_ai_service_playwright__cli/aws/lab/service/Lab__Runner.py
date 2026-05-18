# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Runner
# Orchestrates a single experiment: setup → execute → teardown.
# Also owns create_and_register() which writes a ledger entry BEFORE invoking
# the resource factory (so the sweeper can clean up even after a crash).
# ═══════════════════════════════════════════════════════════════════════════════

import atexit
import signal
import uuid
from datetime  import datetime, timezone, timedelta
from typing    import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State        import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Experiment__Status  import Enum__Lab__Experiment__Status
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type       import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Int__Duration_Ms     import Safe_Int__Duration_Ms
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id   import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id     import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry   import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Run__Result     import Schema__Lab__Run__Result
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                  import Lab__Ledger
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Timing                  import Lab__Timing
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Dispatcher import Lab__Teardown__Dispatcher
from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Timing__Sample import List__Schema__Lab__Timing__Sample

_DEFAULT_TTL_MINUTES = 60


def _make_run_id() -> str:
    ts    = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    nonce = uuid.uuid4().hex[:6]
    return f'{ts}__{nonce}'


class Lab__Runner(Type_Safe):
    ledger     : Lab__Ledger
    dispatcher : Lab__Teardown__Dispatcher
    run_id     : str = ''
    ttl_minutes: int = _DEFAULT_TTL_MINUTES

    def setup(self) -> 'Lab__Runner':
        if not self.ledger.ledger_path:
            self.ledger.setup()
        if self.dispatcher is None:
            self.dispatcher = Lab__Teardown__Dispatcher()
            self.dispatcher.setup()
        if not self.run_id:
            self.run_id = _make_run_id()
        self._register_signal_handlers()
        return self

    # ── resource registration (write-before-create pattern) ──────────────────

    def create_and_register(self,
                            resource_type  : Enum__Lab__Resource_Type,
                            resource_id    : str,
                            experiment     : str,
                            factory        : Callable,
                            region         : str = '',
                            extra          : str = '') -> object:
        entry = self._make_entry(resource_type, resource_id, experiment, region, extra)
        self.ledger.append(entry)                                                   # written BEFORE factory call
        try:
            result = factory()
            return result
        except Exception:
            self.ledger.update_state(str(entry.entry_id), Enum__Lab__Entry__State.FAILED)
            raise

    # ── experiment execution ──────────────────────────────────────────────────

    def run(self, experiment) -> Schema__Lab__Run__Result:
        timing = Lab__Timing().start()
        started_at = datetime.now(timezone.utc).isoformat()
        experiment.setup(self)
        try:
            result = experiment.execute()
        except Exception as ex:
            finished_at = datetime.now(timezone.utc).isoformat()
            return Schema__Lab__Run__Result(
                run_id      = Safe_Str__Lab__Run_Id(self.run_id),
                status      = Enum__Lab__Experiment__Status.FAILED,
                started_at  = started_at,
                finished_at = finished_at,
                duration_ms = Safe_Int__Duration_Ms(timing.elapsed_ms()),
                samples     = List__Schema__Lab__Timing__Sample(),
                error       = str(ex),
                notes       = '',
            )
        finally:
            self._teardown_all()
        return result

    # ── teardown ─────────────────────────────────────────────────────────────

    def _teardown_all(self) -> None:
        pending = self.ledger.entries_for_run(self.run_id)
        for entry in pending:
            if entry.state == Enum__Lab__Entry__State.PENDING:
                try:
                    self.dispatcher.teardown(entry)
                    self.ledger.update_state(str(entry.entry_id), Enum__Lab__Entry__State.DELETED)
                except Exception:
                    pass                                                            # sweeper covers leftovers

    # ── private ───────────────────────────────────────────────────────────────

    def _make_entry(self,
                    resource_type : Enum__Lab__Resource_Type,
                    resource_id   : str,
                    experiment    : str,
                    region        : str,
                    extra         : str) -> Schema__Lab__Ledger__Entry:
        now        = datetime.now(timezone.utc)
        expires_at = (now + timedelta(minutes=self.ttl_minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')
        entry_id   = uuid.uuid4().hex
        return Schema__Lab__Ledger__Entry(
            entry_id      = Safe_Str__Lab__Entry_Id(entry_id),
            run_id        = Safe_Str__Lab__Run_Id(self.run_id),
            resource_type = resource_type,
            resource_id   = Safe_Str__AWS__ARN(resource_id),
            region        = Safe_Str__AWS__Region(region),
            created_at    = now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            expires_at    = expires_at,
            state         = Enum__Lab__Entry__State.PENDING,
            experiment    = experiment,
            extra         = extra,
        )

    def _register_signal_handlers(self) -> None:                                   # layers 2 + 3 of the safety model
        atexit.register(self._teardown_all)
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, lambda signum, frame: self._teardown_all())
            except (OSError, ValueError):
                pass                                                                # can't set signal handler in non-main thread
