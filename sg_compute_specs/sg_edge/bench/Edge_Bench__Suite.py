# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Edge_Bench__Suite
# Orchestrates doc-05 bench runs: resolve a scenario id / tier / "all" from the
# registry, run each N times through Edge_Bench__Runner against the chosen target,
# and assemble a Schema__Edge_Bench__Suite_Result (metrics + verdicts + pass flag).
#
# LOCAL scenarios run in-process against a fresh temp-dir `sg edge local` stack
# (cleaned up after). AWS_BENCH scenarios are skipped with a clear note — their
# execution backend is Slice-5/6 live-AWS and is not built. Fail-fast, no retries
# (doc-05 decision #3): a scenario whose run fn raises is marked failed with the
# error, not retried.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile
import uuid
from time import strftime

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sg_compute_specs.sg_edge.bench.Edge_Bench__Runner                            import Edge_Bench__Runner
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target                import Enum__Edge_Bench__Target
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier                  import Enum__Edge_Bench__Tier
from sg_compute_specs.sg_edge.bench.scenarios.Edge_Bench__Scenarios               import SCENARIOS, descriptors
from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Scenario_Result   import Schema__Edge_Bench__Scenario_Result
from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Suite_Result      import Schema__Edge_Bench__Suite_Result


class Edge_Bench__Suite(Type_Safe):
    runner : Edge_Bench__Runner

    # ── listing ───────────────────────────────────────────────────────────────

    def list(self, target=None, tier=None) -> list:
        return descriptors(target=target, tier=tier)

    # ── single scenario ───────────────────────────────────────────────────────

    def run_scenario(self, scenario_id: str,
                           repeat   : int = 5,
                           target   : Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL
                     ) -> Schema__Edge_Bench__Scenario_Result:
        scenario_id = scenario_id.strip().upper()
        if scenario_id not in SCENARIOS:
            raise ValueError(f'unknown scenario {scenario_id!r} — known: {", ".join(SCENARIOS)}')
        entry  = SCENARIOS[scenario_id]
        desc   = entry['descriptor']
        result = Schema__Edge_Bench__Scenario_Result(id=desc.id, name=desc.name,
                                                     tier=desc.tier, target=target)

        if target != desc.target or entry['make'] is None:                           # can't run this scenario on the chosen target
            result.skipped = True
            result.note    = (f'aws-bench scenario — live backend not built (Slice 5/6)'
                              if desc.target == Enum__Edge_Bench__Target.AWS_BENCH
                              else f'no {target} implementation')
            return result

        state_dir = tempfile.mkdtemp(prefix='sg-edge-bench-')
        try:
            run_once = entry['make'](state_dir)
            outcome  = self.runner.run(run_once, repeat, entry['thresholds'])
            for metric in outcome['metrics']:
                result.metrics.append(metric)
            result.runs   = repeat
            result.passed = bool(outcome['passed'])
        except Exception as exc:                                                     # fail-fast: a wrong outcome / error fails the scenario
            result.passed = False
            result.note   = f'{type(exc).__name__}: {exc}'
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)
        return result

    # ── groups ─────────────────────────────────────────────────────────────────

    def run_ids(self, ids: list, repeat: int = 5,
                      target: Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL) -> Schema__Edge_Bench__Suite_Result:
        suite = Schema__Edge_Bench__Suite_Result(run_id=self._run_id(), target=target)
        for scenario_id in ids:
            suite.results.append(self.run_scenario(scenario_id, repeat=repeat, target=target))
        suite.passed = all(r.passed for r in suite.results if not r.skipped)
        return suite

    def run_tier(self, tier: Enum__Edge_Bench__Tier, repeat: int = 5,
                      target: Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL) -> Schema__Edge_Bench__Suite_Result:
        ids = [d.id for d in descriptors(tier=tier)]
        return self.run_ids(ids, repeat=repeat, target=target)

    def run_all(self, repeat: int = 5,
                      target: Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL) -> Schema__Edge_Bench__Suite_Result:
        return self.run_ids(list(SCENARIOS.keys()), repeat=repeat, target=target)

    # ── internal ─────────────────────────────────────────────────────────────────

    def _run_id(self) -> str:
        return f'{strftime("%Y%m%dT%H%M%S")}-{uuid.uuid4().hex[:4]}'
