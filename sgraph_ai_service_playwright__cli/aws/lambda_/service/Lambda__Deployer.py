# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__Deployer
# Deploys or updates a Lambda function from a local folder by zipping it and
# calling create_function / update_function_code via boto3.
#
# EXCEPTION — using boto3 directly (see Lambda__AWS__Client header for reason).
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import io
import os
import shutil
import tempfile
import time
import zipfile
from typing import Callable, Optional

import boto3                                                                          # EXCEPTION — see module header
from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Arn           import Safe_Str__Lambda__Arn
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name          import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request    import Schema__Lambda__Deploy__Request
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Response   import Schema__Lambda__Deploy__Response


class Lambda__Deployer(Type_Safe):
    region : str = ''

    def client(self):                                                                  # boto3 seam — subclass overrides to inject fake
        kwargs = {}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.client('lambda', **kwargs)

    def _wait_for_update(self, lc, name: str, timeout_sec: int = 60) -> None:       # polls until LastUpdateStatus != InProgress
        deadline = time.time() + timeout_sec
        delay    = 1
        while time.time() < deadline:
            cfg    = lc.get_function(FunctionName=name)['Configuration']
            status = cfg.get('LastUpdateStatus', 'Successful')
            if status != 'InProgress':
                return
            time.sleep(delay)
            delay = min(delay * 2, 8)
        raise TimeoutError(f'Lambda {name} did not finish updating within {timeout_sec}s')

    def deploy_from_folder(self, req          : Schema__Lambda__Deploy__Request,
                           *,
                           package_root  : str        = '',
                           extra_modules : list        = None,
                           layers        : list        = None,
                           environment   : dict        = None,
                           progress      : 'Optional[Callable[[str, str], None]]' = None,
                           ) -> Schema__Lambda__Deploy__Response:
        # progress(phase, status) is called at every observable phase boundary
        # so a CLI can render a live progress table. Phases (in order):
        #   build-zip / detect-function / upload-code / wait-upload /
        #   update-config / create-function / refresh
        # status is one of: 'start', 'done'. No-op when progress is None.
        def _p(phase: str, status: str) -> None:
            if progress:
                try: progress(phase, status)
                except Exception: pass

        name = str(req.name)

        _p('build-zip', 'start')
        code = self._build_zip(req.folder_path, package_root=package_root, extra_modules=extra_modules)
        _p('build-zip', 'done')

        lc = self.client()
        _p('detect-function', 'start')
        try:
            lc.get_function(FunctionName=name)
            existing = True
        except ClientError as exc:
            err_code = exc.response.get('Error', {}).get('Code', '')
            if err_code == 'ResourceNotFoundException':
                existing = False
            else:
                raise
        _p('detect-function', 'done')

        if existing:
            _p('wait-prior-update', 'start')
            self._wait_for_update(lc, name)                                         # wait for any in-progress update before code upload
            _p('wait-prior-update', 'done')

            _p('upload-code', 'start')
            lc.update_function_code(FunctionName=name, ZipFile=code)
            _p('upload-code', 'done')

            _p('wait-upload', 'start')
            self._wait_for_update(lc, name)                                         # wait for code upload before config update
            _p('wait-upload', 'done')

            _p('update-config', 'start')
            update_kwargs = dict(
                FunctionName = name,
                Handler      = req.handler,
                Runtime      = str(req.runtime),
                Timeout      = req.timeout,
                MemorySize   = req.memory_size,
                Description  = req.description,
            )
            if layers is not None:
                update_kwargs['Layers'] = layers
            if environment is not None:
                update_kwargs['Environment'] = {'Variables': environment}
            lc.update_function_configuration(**update_kwargs)
            _p('update-config', 'done')

            _p('refresh', 'start')
            resp = lc.get_function(FunctionName=name)
            arn  = resp['Configuration']['FunctionArn']
            _p('refresh', 'done')
        else:
            _p('create-function', 'start')
            create_kwargs = dict(
                FunctionName = name,
                Runtime      = str(req.runtime),
                Role         = req.role_arn,
                Handler      = req.handler,
                Code         = {'ZipFile': code},
                Timeout      = req.timeout,
                MemorySize   = req.memory_size,
                Description  = req.description,
            )
            if layers is not None:
                create_kwargs['Layers'] = layers
            if environment is not None:
                create_kwargs['Environment'] = {'Variables': environment}
            resp = lc.create_function(**create_kwargs)
            arn  = resp['FunctionArn']
            _p('create-function', 'done')

        return Schema__Lambda__Deploy__Response(
            name         = Safe_Str__Lambda__Name(name),
            function_arn = Safe_Str__Lambda__Arn(arn) if arn.startswith('arn:') else Safe_Str__Lambda__Arn(''),
            created      = not existing,
            success      = True,
            message      = 'created' if not existing else 'updated',
            zip_size     = len(code),
        )

    def _build_zip(self, folder_path: str, package_root: str = '', extra_modules: list = None) -> bytes:
        extra_modules = extra_modules or []
        root          = package_root if package_root else folder_path
        with tempfile.TemporaryDirectory() as tmp:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                dirnames[:] = [d for d in dirnames if d != '__pycache__']
                for filename in filenames:
                    if filename.endswith('.pyc'):
                        continue
                    abs_path = os.path.join(dirpath, filename)
                    arc_path = os.path.relpath(abs_path, root)
                    target   = os.path.join(tmp, arc_path)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(abs_path, target)

            missing_modules = []
            for module_name in extra_modules:
                try:
                    module = importlib.import_module(module_name)
                except ImportError:
                    # Loud: missing extra_modules cause runtime "ModuleNotFoundError"
                    # in the Lambda. Surfacing it at build time saves a deploy +
                    # cold-start cycle (~5 min) of debugging.
                    missing_modules.append(module_name)
                    continue
                if hasattr(module, '__path__'):
                    # Package — copy the whole directory.
                    src  = module.__path__[0]
                    dest = os.path.join(tmp, os.path.basename(src))
                    if not os.path.exists(dest):
                        shutil.copytree(src, dest,
                                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                elif hasattr(module, '__file__') and module.__file__:
                    # Single-file module — copy the .py file. Required for
                    # things like typing_extensions which are not packages.
                    src  = module.__file__
                    dest = os.path.join(tmp, os.path.basename(src))
                    if not os.path.exists(dest):
                        shutil.copy2(src, dest)
            if missing_modules:
                raise RuntimeError(
                    f'extra_modules not importable in the build environment: '
                    f'{missing_modules!r}. Install them via `pip install <module>` '
                    f'before deploying, OR remove from extra_modules if the import '
                    f'name is wrong (e.g. python-multipart imports as python_multipart).')

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root_dir, dirs, files in os.walk(tmp):
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    for file in files:
                        if file.endswith('.pyc'):
                            continue
                        abs_path = os.path.join(root_dir, file)
                        arc_path = os.path.relpath(abs_path, tmp)
                        zf.write(abs_path, arc_path)
            return buf.getvalue()
