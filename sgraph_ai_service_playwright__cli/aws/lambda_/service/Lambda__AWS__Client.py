# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__AWS__Client
# Sole boto3 boundary for Lambda read + URL operations. Deployment is in
# Lambda__Deployer (handles folder packaging + upload).
#
# EXCEPTION — osbot_aws.aws.lambda_.Lambda is too large to compose cleanly;
# using boto3 directly gives us one thin, mockable boundary. Migrate to
# osbot_aws.Lambda once it stabilises further.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json

import boto3                                                                          # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.collections.List__Schema__Lambda__Function import List__Schema__Lambda__Function
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime                import Enum__Lambda__Runtime
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__State                  import Enum__Lambda__State
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Url__Auth_Type         import Enum__Lambda__Url__Auth_Type
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Arn           import Safe_Str__Lambda__Arn
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name          import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Url           import Safe_Str__Lambda__Url
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Action__Response   import Schema__Lambda__Action__Response
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Alias              import Schema__Lambda__Alias
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Function           import Schema__Lambda__Function
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Function__Details  import Schema__Lambda__Function__Details
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Invoke__Response   import Schema__Lambda__Invoke__Response
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Update__Response   import Schema__Lambda__Update__Response
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Url__Info          import Schema__Lambda__Url__Info
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Version            import Schema__Lambda__Version


class Lambda__AWS__Client(Type_Safe):
    region : str = ''                                                                  # Override to target a specific region

    def client(self):                                                                  # Single boto3 seam — subclass overrides to inject fake
        kwargs = {}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.client('lambda', **kwargs)

    # ── read ──────────────────────────────────────────────────────────────────

    def list_functions(self) -> List__Schema__Lambda__Function:
        lc     = self.client()
        pager  = lc.get_paginator('list_functions')
        result = List__Schema__Lambda__Function()
        for page in pager.paginate():
            for f in page.get('Functions', []):
                result.append(self._parse_function(f))
        return result

    def get_function(self, name: str) -> Schema__Lambda__Function:
        resp = self.client().get_function(FunctionName=name)
        return self._parse_function(resp['Configuration'])

    def get_function_details(self, name: str) -> Schema__Lambda__Function__Details:
        resp = self.client().get_function(FunctionName=name)
        cfg  = resp.get('Configuration', {})
        return self._parse_function_details(cfg)

    def exists(self, name: str) -> bool:
        try:
            self.client().get_function(FunctionName=name)
            return True
        except Exception:
            return False

    def list_versions(self, name: str) -> list:
        lc      = self.client()
        pager   = lc.get_paginator('list_versions_by_function')
        results = []
        for page in pager.paginate(FunctionName=name):
            for v in page.get('Versions', []):
                results.append(Schema__Lambda__Version(
                    name          = Safe_Str__Lambda__Name(v.get('FunctionName', '')),
                    version       = v.get('Version', ''),
                    description   = v.get('Description', ''),
                    last_modified = str(v.get('LastModified', '')),
                    code_size     = v.get('CodeSize', 0),
                ))
        return results

    def list_aliases(self, name: str) -> list:
        lc      = self.client()
        pager   = lc.get_paginator('list_aliases')
        results = []
        for page in pager.paginate(FunctionName=name):
            for a in page.get('Aliases', []):
                results.append(Schema__Lambda__Alias(
                    name             = Safe_Str__Lambda__Name(name),
                    alias_name       = a.get('Name', ''),
                    function_version = a.get('FunctionVersion', ''),
                    description      = a.get('Description', ''),
                ))
        return results

    def list_tags(self, arn: str) -> dict:
        try:
            resp = self.client().list_tags(Resource=arn)
            return resp.get('Tags', {})
        except Exception:
            return {}

    def tag_resource(self, arn: str, tags: dict) -> bool:
        try:
            self.client().tag_resource(Resource=arn, Tags=tags)
            return True
        except Exception:
            return False

    def untag_resource(self, arn: str, keys: list) -> bool:
        try:
            self.client().untag_resource(Resource=arn, TagKeys=keys)
            return True
        except Exception:
            return False

    def invoke(self, name: str, payload: bytes = b'{}',
               async_: bool = False, log_type: str = 'None') -> Schema__Lambda__Invoke__Response:
        invocation_type = 'Event' if async_ else 'RequestResponse'
        try:
            resp = self.client().invoke(
                FunctionName   = name,
                InvocationType = invocation_type,
                Payload        = payload,
                LogType        = log_type,
            )
            status_code    = resp.get('StatusCode', 0)
            function_error = resp.get('FunctionError', '')
            raw_payload    = resp.get('Payload', None)
            payload_str    = ''
            if raw_payload:
                payload_str = raw_payload.read().decode('utf-8')
            log_tail_str = ''
            raw_log = resp.get('LogResult', '')
            if raw_log:
                log_tail_str = base64.b64decode(raw_log).decode('utf-8', errors='replace')
            return Schema__Lambda__Invoke__Response(
                name           = Safe_Str__Lambda__Name(name),
                status_code    = status_code,
                payload        = payload_str,
                function_error = function_error,
                log_tail       = log_tail_str,
                success        = status_code in (200, 202, 204),
                message        = function_error or 'ok',
            )
        except Exception as e:
            return Schema__Lambda__Invoke__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = False,
                message = str(e),
            )

    def update_function_configuration(self, name: str, **fields) -> Schema__Lambda__Update__Response:
        allowed = {'Handler', 'Runtime', 'Timeout', 'MemorySize', 'Description', 'Environment'}
        kwargs  = {k: v for k, v in fields.items() if k in allowed}
        kwargs['FunctionName'] = name
        try:
            self.client().update_function_configuration(**kwargs)
            return Schema__Lambda__Update__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = True,
                message = 'updated',
            )
        except Exception as e:
            return Schema__Lambda__Update__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = False,
                message = str(e),
            )

    # ── URL management ────────────────────────────────────────────────────────

    def get_function_url(self, name: str) -> Schema__Lambda__Url__Info:
        try:
            resp = self.client().get_function_url_config(FunctionName=name)
            return self._parse_url_info(name, resp)
        except Exception:
            return Schema__Lambda__Url__Info(name=Safe_Str__Lambda__Name(name), exists=False)

    def create_function_url(self, name: str,
                             auth_type: Enum__Lambda__Url__Auth_Type = Enum__Lambda__Url__Auth_Type.NONE
                             ) -> Schema__Lambda__Url__Info:
        resp = self.client().create_function_url_config(
            FunctionName = name,
            AuthType     = str(auth_type),
        )
        if str(auth_type) == 'NONE':
            self.client().add_permission(
                FunctionName           = name,
                StatementId            = 'FunctionURLAllowPublicAccess',
                Action                 = 'lambda:InvokeFunctionUrl',
                Principal              = '*',
                FunctionUrlAuthType    = 'NONE',
            )
        return self._parse_url_info(name, resp)

    def delete_function_url(self, name: str) -> Schema__Lambda__Action__Response:
        try:
            self.client().delete_function_url_config(FunctionName=name)
            return Schema__Lambda__Action__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = True,
                message = 'url deleted',
            )
        except Exception as e:
            return Schema__Lambda__Action__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = False,
                message = str(e),
            )

    def delete_function(self, name: str) -> Schema__Lambda__Action__Response:
        try:
            self.client().delete_function(FunctionName=name)
            return Schema__Lambda__Action__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = True,
                message = 'deleted',
            )
        except Exception as e:
            return Schema__Lambda__Action__Response(
                name    = Safe_Str__Lambda__Name(name),
                success = False,
                message = str(e),
            )

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_runtime(self, raw: str) -> Enum__Lambda__Runtime:
        try:
            return Enum__Lambda__Runtime(raw)
        except ValueError:
            return Enum__Lambda__Runtime.PYTHON_3_11

    def _parse_state(self, raw: str) -> Enum__Lambda__State:
        try:
            return Enum__Lambda__State(raw)
        except ValueError:
            return Enum__Lambda__State.PENDING

    def _parse_function(self, cfg: dict) -> Schema__Lambda__Function:
        return Schema__Lambda__Function(
            name          = Safe_Str__Lambda__Name(cfg.get('FunctionName', '')),
            function_arn  = Safe_Str__Lambda__Arn(cfg.get('FunctionArn', '') if cfg.get('FunctionArn', '').startswith('arn:') else ''),
            runtime       = self._parse_runtime(cfg.get('Runtime', '')),
            state         = self._parse_state(cfg.get('State', 'Active')),
            handler       = cfg.get('Handler', ''),
            description   = cfg.get('Description', ''),
            memory_size   = cfg.get('MemorySize', 128),
            timeout       = cfg.get('Timeout', 60),
            last_modified = str(cfg.get('LastModified', '')),
        )

    def _parse_function_details(self, cfg: dict) -> Schema__Lambda__Function__Details:
        env_raw   = cfg.get('Environment', {}).get('Variables', {})
        layers    = [l.get('Arn', '') for l in cfg.get('Layers', [])]
        tracing   = cfg.get('TracingConfig', {}).get('Mode', '')
        eph       = cfg.get('EphemeralStorage', {}).get('Size', 512)
        arch_list = cfg.get('Architectures', [])
        arch      = arch_list[0] if arch_list else ''
        return Schema__Lambda__Function__Details(
            name              = Safe_Str__Lambda__Name(cfg.get('FunctionName', '')),
            function_arn      = Safe_Str__Lambda__Arn(cfg.get('FunctionArn', '') if cfg.get('FunctionArn', '').startswith('arn:') else ''),
            runtime           = self._parse_runtime(cfg.get('Runtime', '')),
            state             = self._parse_state(cfg.get('State', 'Active')),
            handler           = cfg.get('Handler', ''),
            description       = cfg.get('Description', ''),
            memory_size       = cfg.get('MemorySize', 128),
            timeout           = cfg.get('Timeout', 60),
            last_modified     = str(cfg.get('LastModified', '')),
            code_size         = cfg.get('CodeSize', 0),
            role_arn          = cfg.get('Role', ''),
            environment       = dict(env_raw),
            layers            = layers,
            architecture      = arch,
            kms_key_arn       = cfg.get('KMSKeyArn', ''),
            tracing_mode      = tracing,
            ephemeral_storage = eph,
        )

    def _parse_url_info(self, name: str, resp: dict) -> Schema__Lambda__Url__Info:
        raw_url  = resp.get('FunctionUrl', '')
        raw_auth = resp.get('AuthType', 'NONE')
        try:
            auth = Enum__Lambda__Url__Auth_Type(raw_auth)
        except ValueError:
            auth = Enum__Lambda__Url__Auth_Type.NONE
        return Schema__Lambda__Url__Info(
            name         = Safe_Str__Lambda__Name(name),
            function_url = Safe_Str__Lambda__Url(raw_url) if raw_url else Safe_Str__Lambda__Url(''),
            auth_type    = auth,
            exists       = bool(raw_url),
        )
