# ═══════════════════════════════════════════════════════════════════════════════
# Live integration tests — pytest fixtures + skip-gate.
#
# These tests are black-box HTTP clients. They drive a running sg-playwright
# service (typically the Docker Hub image started as a `services:` sidecar
# in CI, or `docker run` locally) and assert on the wire response.
#
# Required env vars — when any is missing the whole tier is skipped so the
# default `pytest tests/` run on a contributor laptop stays hermetic:
#   SG_PLAYWRIGHT__LIVE_BASE_URL    Base URL of the running service
#                                   (e.g. http://localhost:8000)
#   SG_PLAYWRIGHT__LIVE_API_KEY     Value for the X-API-Key header (matches
#                                   FAST_API__AUTH__API_KEY__VALUE on the
#                                   service container)
#
# Optional:
#   SG_PLAYWRIGHT__LIVE_API_KEY_NAME  Header name; defaults to 'X-API-Key'
#
# Targets used by the suite (all CDN-hosted, no compute concern from PR-
# frequency runs):
#   https://example.com         — RFC-safe stability sentinel
#   https://sgraph.ai           — own marketing site
#   https://send.sgraph.ai      — real product surface (real JS)
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest
import httpx


ENV__BASE_URL      = 'SG_PLAYWRIGHT__LIVE_BASE_URL'
ENV__API_KEY       = 'SG_PLAYWRIGHT__LIVE_API_KEY'
ENV__API_KEY_NAME  = 'SG_PLAYWRIGHT__LIVE_API_KEY_NAME'
DEFAULT_KEY_HEADER = 'X-API-Key'

TARGET__SGRAPH     = 'https://sgraph.ai/'                                                # Marketing site — lightest of the three, used as the default smoke target
TARGET__SEND       = 'https://send.sgraph.ai/'                                           # Real product UI — heavier JS, used to validate live-app paths
TARGET__VAULT_URL  = 'https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b'    # BUG-1 sentinel — the URL shape that crashed the @Content driving session
TARGET__ALL_SGRAPH = [TARGET__SGRAPH, TARGET__SEND]                                       # Convenience list for tests that hit "every target"

REQUEST_TIMEOUT_S  = 60.0                                                                # Real browser launches dominate; 60s leaves slack for cold-start


def _base_url() -> str:
    return os.environ.get(ENV__BASE_URL, '').rstrip('/')


def _api_key() -> str:
    return os.environ.get(ENV__API_KEY, '')


def _api_key_header() -> str:
    return os.environ.get(ENV__API_KEY_NAME, DEFAULT_KEY_HEADER)


_SKIP_REASON = f'Set {ENV__BASE_URL} + {ENV__API_KEY} to run live integration tests.'


def pytest_configure(config):                                                            # Register the `serial` marker so pytest-xdist + the test files agree on the schedule
    config.addinivalue_line('markers',
        'serial: must run sequentially in a single xdist worker (shared session state)')


def pytest_collection_modifyitems(config, items):
    # 1) Skip-gate when env vars are unset (laptop default)
    if not (_base_url() and _api_key()):
        skip_marker = pytest.mark.skip(reason=_SKIP_REASON)
        for item in items:
            item.add_marker(skip_marker)
        return

    # 2) pytest-xdist: pin serial-marked tests to ONE worker. Session tests
    #    are stateful (open → act → probe → close on the same session_id) so
    #    they can't be sharded across workers. We use `xdist_group` to force
    #    all `serial`-marked tests onto the same scheduler bucket.
    try:
        import xdist                                                                      # only present when pytest-xdist is installed (CI install)
    except ImportError:
        return
    for item in items:
        if item.get_closest_marker('serial') is not None:
            item.add_marker(pytest.mark.xdist_group('serial'))


@pytest.fixture(scope='session')
def base_url() -> str:
    return _base_url()


@pytest.fixture(scope='session')
def client() -> httpx.Client:                                                             # Session-scoped — re-uses TCP connection across tests
    headers = {_api_key_header(): _api_key()}
    with httpx.Client(base_url=_base_url(),
                      headers=headers,
                      timeout=REQUEST_TIMEOUT_S) as c:
        yield c
