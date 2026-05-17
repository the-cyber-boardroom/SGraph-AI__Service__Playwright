# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Slug__Registry
# SSM-backed registry of published slugs. One parameter per slug at:
#   /sg-compute/vault-publish/slugs/{slug}
# Value is JSON of Schema__Vault_Publish__Entry fields.
# Factory seam (_param_factory) enables in-memory composition in tests.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timezone
from typing   import Callable, List, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug              import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key        import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Entry import Schema__Vault_Publish__Entry

SSM_PREFIX = '/sg-compute/vault-publish/slugs'


class Slug__Registry(Type_Safe):
    _param_factory: Optional[Callable] = None  # seam: (name: str) -> Parameter-like

    def _param(self, slug: str):
        name = f'{SSM_PREFIX}/{slug}'
        if self._param_factory is not None:
            return self._param_factory(name)
        from osbot_aws.helpers.Parameter import Parameter
        return Parameter(name)

    def _all_slug_names(self) -> List[str]:
        if self._param_factory is not None:
            return self._param_factory(None).list_under_prefix(SSM_PREFIX)
        from osbot_aws.helpers.Parameter import Parameter
        p = Parameter()
        try:
            return [n for n in (p.ssm().get_paginator('describe_parameters')
                                .paginate(ParameterFilters=[{'Key': 'Path', 'Values': [SSM_PREFIX]}])
                                .build_full_result()
                                .get('Parameters', []))
                    if n.get('Name', '').startswith(SSM_PREFIX + '/')]
        except Exception:
            return []

    def put(self, slug: str, vault_key: str, stack_name: str,
            fqdn: str, region: str) -> bool:
        entry = {
            'slug'      : slug,
            'vault_key' : vault_key,
            'stack_name': stack_name,
            'fqdn'      : fqdn,
            'region'    : region,
            'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        try:
            self._param(slug).put(json.dumps(entry))
            return True
        except Exception:
            return False

    def get(self, slug: str) -> Optional[Schema__Vault_Publish__Entry]:
        raw = self._param(slug).value()
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return Schema__Vault_Publish__Entry(
                slug       = Safe_Str__Slug(data.get('slug', '')),
                vault_key  = Safe_Str__Vault__Key(data.get('vault_key', '')),
                stack_name = data.get('stack_name', ''),
                fqdn       = data.get('fqdn', ''),
                region     = data.get('region', ''),
                created_at = data.get('created_at', ''),
            )
        except Exception:
            return None

    def delete(self, slug: str) -> bool:
        return self._param(slug).delete()

    def list_all(self) -> List[str]:
        names = self._all_slug_names()
        return [n.get('Name', n).split('/')[-1] for n in names if n]
