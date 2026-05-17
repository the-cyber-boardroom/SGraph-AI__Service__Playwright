# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Aws__Region__Resolver
# Region precedence (highest → lowest):
#   1. --region flag on the command
#   2. resource hint (e.g. ARN-embedded region)
#   3. SG_AWS__REGION env var
#   4. Active role's region from the credentials store
#   5. AWS_DEFAULT_REGION env var
#   6. 'us-east-1' hard fallback
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Aws__Region__Resolver(Type_Safe):

    def resolve(self, region_flag: str = '', resource_hint: str = '') -> Safe_Str__AWS__Region:
        candidates = [
            region_flag,
            resource_hint,
            os.environ.get('SG_AWS__REGION', ''),
            self._role_region(),
            os.environ.get('AWS_DEFAULT_REGION', ''),
            'us-east-1',
        ]
        for c in candidates:
            if c:
                return Safe_Str__AWS__Region(c)
        return Safe_Str__AWS__Region('us-east-1')

    def _role_region(self) -> str:
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context  import Sg__Aws__Context
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            role_name = Sg__Aws__Context.get_current_role()
            if role_name:
                config = Credentials__Store().role_get(role_name)
                if config and hasattr(config, 'region'):
                    return str(config.region) if config.region else ''
        except Exception:
            pass
        return ''
