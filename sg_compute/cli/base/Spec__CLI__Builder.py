# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Builder
# Factory that produces a fully-wired typer.Typer for one spec.  Each
# Cli__{Pascal}.py is a small call into this builder.
#
# The builder is NOT a Type_Safe — typer reflects on function annotations
# via inspect.signature which conflicts with Type_Safe's metaclass. (Risk R1)
# ═══════════════════════════════════════════════════════════════════════════════

import inspect
import os
from typing import Any, List, Optional, Tuple

import typer
from rich.console import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec  import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Defaults      import (DEFAULT_EXEC_TIMEOUT ,
                                                           DEFAULT_MAX_HOURS    ,
                                                           DEFAULT_POLL_SEC     ,
                                                           DEFAULT_REGION       ,
                                                           DEFAULT_TIMEOUT_SEC  )
from sg_compute.cli.base.Spec__CLI__Errors        import set_debug, spec_cli_errors
from sg_compute.cli.base.Spec__CLI__Renderers__Base import (render_create      ,
                                                             render_delete      ,
                                                             render_exec_result ,
                                                             render_health_probe,
                                                             render_info        ,
                                                             render_list        )
from sg_compute.cli.base.Spec__CLI__Resolver      import Spec__CLI__Resolver


class Spec__CLI__Builder:

    def __init__(self, cli_spec: Schema__Spec__CLI__Spec,
                       extra_create_options: Optional[List[Tuple[str, type, Any, str]]] = None):
        self.cli_spec             = cli_spec
        self.extra_create_options = extra_create_options or []
        self.resolver             = Spec__CLI__Resolver()

    def build(self) -> typer.Typer:
        app = typer.Typer(no_args_is_help  = True                                       ,
                          help             = f'Manage {self.cli_spec.display_name} stacks.',
                          add_completion   = False                                       )

        @app.callback()
        def _root(debug: bool = typer.Option(False, '--debug', '-D',
                                             help='Show full Python traceback on errors.')):
            set_debug(debug)

        self._register_list   (app)
        self._register_info   (app)
        self._register_create (app)
        self._register_wait   (app)
        self._register_health (app)
        self._register_connect(app)
        self._register_exec   (app)
        self._register_delete (app)
        return app

    # ── internal helpers ──────────────────────────────────────────────────────

    def _service(self):
        return self.cli_spec.service_factory()

    def _build_typed_fn(self, impl, params: List[Tuple[str, type, Any]], name: str):
        parameters = [
            inspect.Parameter(pname, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                              default=pdefault, annotation=ptype)
            for pname, ptype, pdefault in params
        ]
        sig = inspect.Signature(parameters)

        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            return impl(**bound.arguments)

        wrapper.__signature__ = sig
        wrapper.__name__      = name
        wrapper.__annotations__ = {p.name: p.annotation for p in parameters}
        return wrapper

    def _wait_healthy(self, svc, region: str, stack_name: str) -> None:
        c   = Console(highlight=False)
        c.print(f'\n  [dim]Waiting for {self.cli_spec.spec_id} stack {stack_name!r} to be healthy …[/]')
        result = svc.health(region, stack_name,
                             timeout_sec=DEFAULT_TIMEOUT_SEC, poll_sec=DEFAULT_POLL_SEC)
        render_health_probe(result, c)
        if not getattr(result, 'healthy', False):
            Console(highlight=False, stderr=True).print(
                f'  [red]✗[/]  Stack {stack_name!r} did not become healthy in {DEFAULT_TIMEOUT_SEC}s')
            raise typer.Exit(1)

    # ── verb registrations ────────────────────────────────────────────────────

    def _register_list(self, app):
        service_factory = self.cli_spec.service_factory

        @app.command(name='list')
        @spec_cli_errors
        def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r',
                                                   help='AWS region.')):
            svc     = service_factory()
            listing = svc.list_stacks(region)
            render_list(listing, Console(highlight=False, width=200))

    def _register_info(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def info(name  : Optional[str] = typer.Argument(None,
                          help='Stack name; auto-selected when only one exists.'),
                 region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            data = svc.get_stack_info(region, name)
            if data is None:
                Console(highlight=False, stderr=True).print(
                    f'  [red]✗  No {spec_id} stack matched {name!r}[/]')
                raise typer.Exit(1)
            render_info(data, Console(highlight=False, width=200))

    def _register_create(self, app):
        cli_spec        = self.cli_spec
        resolver        = self.resolver
        service_factory = self.cli_spec.service_factory
        spec_id         = self.cli_spec.spec_id
        extra_options   = self.extra_create_options

        base_params = [
            ('name',          Optional[str], typer.Argument(None,
                              help='Stack name; auto-generated if omitted.')),
            ('region',        str,           typer.Option(DEFAULT_REGION, '--region', '-r')),
            ('instance_type', str,           typer.Option(cli_spec.default_instance_type,
                                                          '--instance-type', '-t')),
            ('max_hours',     int,           typer.Option(DEFAULT_MAX_HOURS, '--max-hours')),
            ('ami',           str,           typer.Option('', '--ami',
                                            help='AMI ID; resolved from spec helper if blank.')),
            ('caller_ip',     str,           typer.Option('', '--caller-ip',
                                            help='Source IP for SG; auto-detected if blank.')),
            ('wait',          bool,          typer.Option(False, '--wait',
                                            help='Block until healthy after create.')),
        ]
        extra_params = [
            (n, t, typer.Option(d, f'--{n.replace("_", "-")}', help=h))
            for (n, t, d, h) in extra_options
        ]
        all_params = base_params + extra_params

        def create_impl(**kwargs):
            svc    = service_factory()
            region = kwargs['region']
            name   = kwargs.get('name') or (
                svc.name_gen.generate() if hasattr(svc, 'name_gen') else f'{spec_id}-auto')
            req    = cli_spec.create_request_cls()
            if hasattr(req, 'stack_name'):
                setattr(req, 'stack_name', name)
            if hasattr(req, 'region'):
                setattr(req, 'region', region)
            for attr, kwarg in (('instance_type', 'instance_type'),
                                 ('max_hours',     'max_hours'    ),
                                 ('from_ami',      'ami'          ),
                                 ('caller_ip',     'caller_ip'   )):
                if hasattr(req, attr):
                    setattr(req, attr, kwargs[kwarg])
            if cli_spec.extra_create_field_setters:
                cli_spec.extra_create_field_setters(req, **{
                    k: kwargs[k] for (k, _, _, _) in extra_options
                })
            resp       = svc.create_stack(req)
            render_create(resp, Console(highlight=False, width=200))
            if kwargs.get('wait'):
                info      = getattr(resp, 'stack_info', None) or resp
                real_name = str(getattr(info, 'stack_name', '') or name)
                self._wait_healthy(svc, region, real_name)

        fn = self._build_typed_fn(create_impl, all_params, 'create')
        app.command()(spec_cli_errors(fn))

    def _register_wait(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def wait(name   : Optional[str] = typer.Argument(None,
                           help='Stack name; auto-selected when only one exists.'),
                 region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                 timeout: int           = typer.Option(DEFAULT_TIMEOUT_SEC, '--timeout',
                                         help='Max seconds to wait.'),
                 poll   : int           = typer.Option(DEFAULT_POLL_SEC, '--poll',
                                         help='Seconds between polls.')):
            svc    = service_factory()
            name   = resolver.resolve(svc, name, region, spec_id)
            result = svc.health(region, name, timeout_sec=timeout, poll_sec=poll)
            render_health_probe(result, Console(highlight=False, width=200))
            if not getattr(result, 'healthy', False):
                raise typer.Exit(1)

    def _register_health(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def health(name   : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                   region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                   timeout: int           = typer.Option(0, '--timeout',
                                           help='0 = instant probe; >0 = wait up to N seconds.')):
            svc    = service_factory()
            name   = resolver.resolve(svc, name, region, spec_id)
            result = svc.health(region, name, timeout_sec=timeout)
            render_health_probe(result, Console(highlight=False, width=200))

    def _register_connect(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def connect(name  : Optional[str] = typer.Argument(None,
                               help='Stack name; auto-selected when only one exists.'),
                    region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
            svc         = service_factory()
            name        = resolver.resolve(svc, name, region, spec_id)
            instance_id = svc.connect_target(region, name)
            Console(highlight=False).print(
                f'  [dim]Connecting to {name} ({instance_id}) in {region}…[/]\n')
            os.execvp('aws', ['aws', 'ssm', 'start-session',
                               '--target', instance_id, '--region', region])

    def _register_exec(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command(name='exec')
        @spec_cli_errors
        def exec_cmd(name   : Optional[str] = typer.Argument(None,
                                help='Stack name; auto-selected when only one exists.'),
                     command: str           = typer.Argument(...,
                                help='Shell command to run on the instance via SSM.'),
                     region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                     timeout: int           = typer.Option(DEFAULT_EXEC_TIMEOUT, '--timeout'),
                     cwd    : str           = typer.Option('', '--cwd',
                                help='Working directory on the remote host.')):
            svc    = service_factory()
            name   = resolver.resolve(svc, name, region, spec_id)
            result = svc.exec(region, name, command, timeout_sec=timeout, cwd=cwd)
            render_exec_result(result, Console(highlight=False, width=200))

    def _register_delete(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def delete(name  : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                   region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                   yes   : bool          = typer.Option(False, '--yes', '-y',
                              help='Skip confirmation prompt.')):
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            if not yes:
                typer.confirm(f'Delete {spec_id} stack {name!r} in {region}?', default=True, abort=True)
            result = svc.delete_stack(region, name)
            render_delete(name, getattr(result, 'deleted', False),
                          Console(highlight=False, width=200))
            if not getattr(result, 'deleted', False):
                raise typer.Exit(1)
