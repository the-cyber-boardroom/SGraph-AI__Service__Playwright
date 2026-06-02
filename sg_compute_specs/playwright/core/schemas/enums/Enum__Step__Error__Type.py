# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Step__Error__Type
#
# Structured classification of a step failure. Lets clients branch on failure
# class (retry on TIMEOUT, fail-fast on SELECTOR_NOT_FOUND, surface differently
# for NAVIGATION_FAILED) without parsing the free-text error_message. Set by
# Step__Executor.failed_result via classify_error(); UNKNOWN is the safe default
# for unrecognised exception classes.
#
# Members are intentionally narrow — add new categories rather than overloading
# existing ones. Clients should treat any value not in their enum as UNKNOWN.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Step__Error__Type(str, Enum):
    TIMEOUT             = 'timeout'              # Playwright TimeoutError (selector / navigation / wait_for)
    SELECTOR_NOT_FOUND  = 'selector_not_found'   # Element-locating failure that isn't a timeout
    NAVIGATION_FAILED   = 'navigation_failed'    # page.goto() failure (DNS, connection, certificate, etc.)
    EVALUATE_REJECTED   = 'evaluate_rejected'    # JS__Expression__Allowlist denial of an evaluate step
    ASSERTION_FAILED    = 'assertion_failed'     # expect_* native assertion failure
    UNSUPPORTED_ACTION  = 'unsupported_action'   # step.action not in ACTION_HANDLERS (defensive)
    UNKNOWN             = 'unknown'              # Default — exception class not recognised
