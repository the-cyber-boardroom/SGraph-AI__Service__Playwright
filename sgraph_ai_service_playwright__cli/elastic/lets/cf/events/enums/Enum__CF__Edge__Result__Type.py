# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Edge__Result__Type
# CloudFront edge result type (x_edge_detailed_result_type TSV column).
# Drives the "Edge result type breakdown" donut on the events dashboard —
# Hit / Miss tells us cache effectiveness; FunctionGeneratedResponse tells
# us what CloudFront Functions absorbed before reaching origin.
# Other catches values we don't model.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Edge__Result__Type(str, Enum):
    Hit                       = 'Hit'                                                # Cache hit, served from edge
    RefreshHit                = 'RefreshHit'                                         # Stale-but-revalidated hit
    OriginShieldHit           = 'OriginShieldHit'                                    # Hit at the origin shield layer
    Miss                      = 'Miss'                                               # Cache miss, fetched from origin
    LimitExceeded             = 'LimitExceeded'                                      # Throttled
    Redirect                  = 'Redirect'                                           # CloudFront-generated redirect
    Error                     = 'Error'                                              # Origin error or CloudFront-side problem
    FunctionGeneratedResponse = 'FunctionGeneratedResponse'                          # CloudFront Functions returned a synthetic response
    Other                     = 'Other'                                              # Anything we don't model

    def __str__(self):
        return self.value
