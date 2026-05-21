# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Local Docker source + render + screen
# Uses a real Pod__Runtime subclass with a canned list() (no mocks, no daemon) and a
# "down" runtime that raises (daemon unreachable). Asserts the render, the source's
# graceful-empty behaviour, the Deployment LOCAL DOCKER section, and the pilot wiring.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

from sg_compute.host_plane.pods.service.Pod__Runtime                        import Pod__Runtime
from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List, List__Schema__Pod__Info
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Docker__Source       import SG_Edge__TUI__Docker__Source
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Docker__Render      import docker_markup, docker_lines

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False


class Fake_Runtime(Pod__Runtime):
    def list(self) -> Schema__Pod__List:
        pods = List__Schema__Pod__Info()
        pods.append(Schema__Pod__Info(name='sg-edge-proxy', image='openresty:1.25', status='Up 2 hours',           state='running'))
        pods.append(Schema__Pod__Info(name='old-job',       image='busybox',        status='Exited (0) 5 min ago', state='exited'))
        return Schema__Pod__List(pods=pods, count=2)


class Down_Runtime(Pod__Runtime):
    def list(self) -> Schema__Pod__List:
        raise RuntimeError('daemon down')


class test_SG_Edge__TUI__Docker__Source(TestCase):

    def test_containers__lists_running_and_exited(self):
        src  = SG_Edge__TUI__Docker__Source(runtime=Fake_Runtime())
        pods = src.containers()
        assert pods.count == 2
        assert {p.name for p in pods.pods} == {'sg-edge-proxy', 'old-job'}
        assert src.available() is True

    def test_daemon_down__empty_and_unavailable(self):
        src = SG_Edge__TUI__Docker__Source(runtime=Down_Runtime())
        assert len(src.containers().pods) == 0                                       # exception swallowed → honest empty
        assert src.available() is False


class test_docker_render(TestCase):

    def test_markup__rows_and_glyphs(self):
        out = docker_markup(Fake_Runtime().list(), available=True)
        for token in ('Local Docker', 'sg-edge-proxy', 'openresty:1.25', 'Up 2 hours', 'old-job'):
            assert token in out, token
        assert '●' in out and '✗' in out                                            # running vs exited glyphs

    def test_unavailable_note(self):
        assert 'not reachable' in docker_markup(Schema__Pod__List(), available=False)

    def test_empty_when_available(self):
        assert 'no containers running' in '\n'.join(docker_lines(Schema__Pod__List(), available=True))


class test_deployment_includes_docker(TestCase):

    def test_local_docker_section_present_when_containers_passed(self):
        from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot import Schema__SG_Edge__TUI__Snapshot
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Deployment__Render import deployment_markup
        snap = Schema__SG_Edge__TUI__Snapshot(parent='edge.sg-labs.local', captured_at=100, zone_exists=True, wildcard=True)
        with_docker = deployment_markup(snap, Fake_Runtime().list(), True)
        assert 'LOCAL DOCKER'  in with_docker
        assert 'sg-edge-proxy' in with_docker
        assert 'LOCAL DOCKER' not in deployment_markup(snap)                          # omitted when no containers passed (backward compatible)


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__Screen__Docker(TestCase):

    def test_mounts_and_lists(self):
        import asyncio
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Docker import SG_Edge__TUI__Screen__Docker

        async def scenario():
            app = SG_Edge__TUI__Screen__Docker(docker_source=SG_Edge__TUI__Docker__Source(runtime=Fake_Runtime()), refresh_seconds=0)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.containers.count == 2
                await pilot.press('r')
                await pilot.pause()
                await pilot.press('q')
                await pilot.pause()
                assert app.exited is True
        asyncio.run(scenario())
