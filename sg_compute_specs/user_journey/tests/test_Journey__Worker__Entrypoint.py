# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Journey__Worker__Entrypoint + the end-to-end journey-delivery loop
#
# Proves env-JSON delivery round-trips: a planned spec.journey → the Docker runtime's
# SG_UJ__JOURNEY_JSON → back into a Schema__Journey__Definition the entrypoint runs.
# Pure parsing only — run()/main() need a real browser (gated). No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.user_journey.core.conductor.Suite__Runner               import Suite__Runner
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__Docker     import Worker__Runtime__Docker
from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec import Schema__Worker__Spec
from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition import Schema__Journey__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition     import Schema__Suite__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Entry          import Schema__Suite__Entry
from sg_compute_specs.user_journey.core.worker.Journey__Worker__Entrypoint          import Journey__Worker__Entrypoint


def _journey():
    journey            = Schema__Journey__Definition()
    journey.journey_id = 'checkout'
    journey.environment = 'prod'
    journey.target_url  = 'https://shop.test/'
    journey.steps.append({'action': 'goto', 'url': 'https://shop.test/'})
    return journey


def _env_var(args, prefix):                                                         # value of the `-e PREFIX=...` arg
    for arg in args:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    return None


class TestEntrypointEnvParsing:

    def test__run_id_from_env(self):
        run_id = Journey__Worker__Entrypoint().run_id_from_env({'SG_UJ__RUN_ID': 'run-abc'})
        assert str(run_id) == 'run-abc'

    def test__run_id_missing_raises(self):
        with pytest.raises(ValueError):
            Journey__Worker__Entrypoint().run_id_from_env({})

    def test__journey_from_env_round_trip(self):
        import json
        env     = {'SG_UJ__JOURNEY_JSON': json.dumps(_journey().json())}
        journey = Journey__Worker__Entrypoint().journey_from_env(env)
        assert str(journey.journey_id)  == 'checkout'
        assert str(journey.target_url)  == 'https://shop.test/'
        assert list(journey.steps)      == [{'action': 'goto', 'url': 'https://shop.test/'}]

    def test__journey_missing_raises(self):
        with pytest.raises(ValueError):
            Journey__Worker__Entrypoint().journey_from_env({})


class TestEndToEndDelivery:

    def test__plan_attaches_journey_then_docker_env_round_trips(self):
        entry             = Schema__Suite__Entry(count=2, concurrency=2)
        entry.journey_id  = 'checkout'
        entry.worker_image = 'sgraph/uj-worker:1.0'
        suite             = Schema__Suite__Definition()
        suite.entries.append(entry)

        waves = Suite__Runner().plan(suite, journeys={'checkout': _journey()})       # journeys map → spec.journey
        spec  = waves[0][0]
        assert spec.journey is not None
        assert str(spec.journey.journey_id) == 'checkout'

        args      = Worker__Runtime__Docker().docker_run_args(spec)                  # spec.journey → SG_UJ__JOURNEY_JSON
        raw       = _env_var(args, 'SG_UJ__JOURNEY_JSON=')
        assert raw is not None

        recovered = Journey__Worker__Entrypoint().journey_from_env({'SG_UJ__JOURNEY_JSON': raw})
        assert str(recovered.journey_id) == 'checkout'
        assert str(recovered.target_url) == 'https://shop.test/'

    def test__plan_without_journeys_leaves_spec_journey_none(self):
        entry            = Schema__Suite__Entry(count=1, concurrency=1)
        entry.journey_id = 'checkout'
        suite            = Schema__Suite__Definition()
        suite.entries.append(entry)
        spec = Suite__Runner().plan(suite)[0][0]
        assert spec.journey is None                                                  # no map → no journey, no JOURNEY_JSON

    def test__docker_args_omit_journey_json_when_absent(self):
        spec              = Schema__Worker__Spec()
        spec.worker_id    = 'w1'
        spec.worker_image = 'img:1'
        args              = Worker__Runtime__Docker().docker_run_args(spec)
        assert _env_var(args, 'SG_UJ__JOURNEY_JSON=') is None
