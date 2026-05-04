# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Spec__Catalogue
# The full catalogue returned by GET /api/specs.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class Schema__Spec__Catalogue(Type_Safe):
    specs : List[Schema__Spec__Manifest__Entry]
