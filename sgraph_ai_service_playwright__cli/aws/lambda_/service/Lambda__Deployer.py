# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__Deployer
# Deploys or updates a Lambda function from a local folder by zipping it and
# calling create_function / update_function_code via boto3.
#
# EXCEPTION — using boto3 directly (see Lambda__AWS__Client header for reason).
# ═══════════════════════════════════════════════════════════════════════════════

import io
import os
import zipfile

import boto3                                                                          # EXCEPTION — see module header

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

    def deploy_from_folder(self, req: Schema__Lambda__Deploy__Request) -> Schema__Lambda__Deploy__Response:
        name  = str(req.name)
        code  = self._zip_folder(req.folder_path)
        lc    = self.client()
        try:
            lc.get_function(FunctionName=name)
            existing = True
        except Exception:
            existing = False
        try:
            if existing:
                lc.update_function_code(FunctionName=name, ZipFile=code)
                lc.update_function_configuration(
                    FunctionName = name,
                    Handler      = req.handler,
                    Runtime      = str(req.runtime),
                    Timeout      = req.timeout,
                    MemorySize   = req.memory_size,
                    Description  = req.description,
                )
                resp = lc.get_function(FunctionName=name)
                arn  = resp['Configuration']['FunctionArn']
            else:
                resp = lc.create_function(
                    FunctionName = name,
                    Runtime      = str(req.runtime),
                    Role         = req.role_arn,
                    Handler      = req.handler,
                    Code         = {'ZipFile': code},
                    Timeout      = req.timeout,
                    MemorySize   = req.memory_size,
                    Description  = req.description,
                )
                arn = resp['FunctionArn']
            return Schema__Lambda__Deploy__Response(
                name         = Safe_Str__Lambda__Name(name),
                function_arn = Safe_Str__Lambda__Arn(arn) if arn.startswith('arn:') else Safe_Str__Lambda__Arn(''),
                created      = not existing,
                success      = True,
                message      = 'created' if not existing else 'updated',
            )
        except Exception as e:
            return Schema__Lambda__Deploy__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = False,
                message = str(e),
            )

    def _zip_folder(self, folder_path: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    abs_path = os.path.join(root, file)
                    arc_path = os.path.relpath(abs_path, folder_path)
                    zf.write(abs_path, arc_path)
        return buf.getvalue()
