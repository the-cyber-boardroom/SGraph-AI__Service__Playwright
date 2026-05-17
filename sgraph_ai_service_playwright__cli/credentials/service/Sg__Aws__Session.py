# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Sg__Aws__Session
# Vends boto3 clients for a named role.
# If the role config has an assume_role_arn, calls STS AssumeRole and caches
# the temporary credentials for the lifetime of this object.
#
# boto3 EXCEPTION: boto3 is used directly here for STS AssumeRole.
# osbot_aws does not expose a STS AssumeRole helper that fits this pattern.
#
# v0.2.28 additions:
#   - _session_name() generates CloudTrail-correlatable session names
#   - from_context() class method reads the global Sg__Aws__Context role
#   - boto3_client_from_context() falls through to bare boto3 when no role set
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid

import boto3                                                        # boto3 EXCEPTION — STS AssumeRole only

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Credentials            import Schema__AWS__Credentials
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                  import Credentials__Store


def _session_name(role_name: str) -> str:                           # sg-<role>-<ts>-<8hex>
    role_part = role_name[:40].replace(' ', '-')
    raw       = f'sg-{role_part}-{int(time.time())}-{uuid.uuid4().hex[:8]}'
    return raw[:64]                                                  # IAM SessionName hard limit


class Sg__Aws__Session(Type_Safe):
    store               : Credentials__Store
    _cached_session     : object = None                             # boto3.Session cache — not Type_Safe-typed

    # ── internal ──────────────────────────────────────────────────────────────

    def _make_base_session(self, creds: Schema__AWS__Credentials, region: str) -> object:
        return boto3.Session(
            aws_access_key_id     = str(creds.access_key),
            aws_secret_access_key = str(creds.secret_key),
            region_name           = region                ,
        )

    def _assume_role(self, base_session: object, config: Schema__AWS__Role__Config) -> object:
        arn          = str(config.assume_role_arn)
        sname        = _session_name(str(config.name))              # correlatable with CloudTrail
        sts_client   = base_session.client('sts')
        response     = sts_client.assume_role(
            RoleArn         = arn   ,
            RoleSessionName = sname ,
        )
        assumed_creds = response['Credentials']
        return boto3.Session(
            aws_access_key_id     = assumed_creds['AccessKeyId']    ,
            aws_secret_access_key = assumed_creds['SecretAccessKey'] ,
            aws_session_token     = assumed_creds['SessionToken']    ,
            region_name           = str(config.region)              ,
        )

    # ── public API ────────────────────────────────────────────────────────────

    def session_for(self, role_name: str) -> object | None:        # returns boto3.Session or None
        config = self.store.role_get(role_name)
        if config is None:
            return None
        creds = self.store.aws_credentials_get(role_name)
        if creds is None:
            return None
        region       = str(config.region) or 'us-east-1'
        base_session = self._make_base_session(creds, region)
        if str(config.assume_role_arn):
            return self._assume_role(base_session, config)
        return base_session

    def boto3_client(self, role_name: str, service_name: str) -> object | None:
        session = self.session_for(role_name)
        if session is None:
            return None
        return session.client(service_name)

    def boto3_client_from_context(self, service_name: str, region: str = '') -> object:
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
        role = Sg__Aws__Context.get_current_role()
        if role:
            client = self.boto3_client(role, service_name)
            if client:
                return client
        kwargs = {}
        if region:
            kwargs['region_name'] = region
        return boto3.client(service_name, **kwargs)                 # fall-through: bare boto3

    # ── class method ──────────────────────────────────────────────────────────

    @classmethod
    def from_context(cls, context=None) -> 'Sg__Aws__Session':
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
        from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS  import Keyring__Mac__OS
        store = Credentials__Store(keyring=Keyring__Mac__OS())
        return cls(store=store)
