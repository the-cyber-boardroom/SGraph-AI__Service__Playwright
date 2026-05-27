# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — conductor_app (the conductor container entry)
#
# `python3 -m sg_compute_specs.user_journey.core.conductor.api.conductor_app` boots the
# conductor: swap the suite runtime to the Docker-socket backend when a daemon is
# reachable (the container mounts /var/run/docker.sock), then serve Fast_API__Conductor
# under uvicorn. `app` is built at import so it's also a `uvicorn …:app` target and is
# unit-testable; configure_runtime() / main() carry the boot-time side effects.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sg_compute_specs.user_journey.core.conductor.api.Fast_API__Conductor import Fast_API__Conductor

app = Fast_API__Conductor().setup().app()                                           # uvicorn target + test handle


def configure_runtime() -> bool:                                                    # swap in the Docker backend when available
    from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__Docker  import Worker__Runtime__Docker, docker_available
    from sg_compute_specs.user_journey.core.conductor.api.routes.Routes__Suites import SUITE_SERVICE
    if docker_available():
        SUITE_SERVICE.runtime = Worker__Runtime__Docker()
        return True
    return False                                                                    # stays on the in-memory backend


def main() -> None:
    import uvicorn
    configure_runtime()
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('SG_UJ__CONDUCTOR_PORT', '8000')))


if __name__ == '__main__':
    main()
