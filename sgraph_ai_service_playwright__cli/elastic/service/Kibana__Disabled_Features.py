# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Kibana__Disabled_Features
# Single source of truth for the Kibana feature ids we hide from the default
# space's side-nav. Used by:
#
#   1. Elastic__User__Data__Builder — bakes a one-shot harden into the EC2
#      cloud-init so the box is ready-to-use without a follow-up CLI call
#      (also makes AMI snapshots self-contained: nothing extra to wire on a
#      fresh launch from the snapshot).
#   2. Kibana__Saved_Objects__Client.disable_space_features — the runtime
#      `sp el harden` fallback for cases where the boot script didn't run
#      (e.g. an older AMI predating this commit, or after a Kibana data wipe).
#
# Keeping the list in one place avoids drift — both the bash and the Python
# paths apply the exact same disabledFeatures.
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_DISABLED_FEATURES = [
    'observability',
    'apm',
    'infrastructure',
    'logs',
    'uptime',
    'siem',
    'securitySolutionAttackDiscovery',
    'securitySolutionAssistant',
    'securitySolutionCases',
    'securitySolutionTimeline',
    'securitySolutionNotes',
    'fleet',
    'fleetv2',
    'osquery',
    'ml',
    'maps',
    'graph',
    'canvas',
    'enterpriseSearch',
    'searchInferenceEndpoints',
    'searchPlayground',
    'searchSynonyms',
    'searchQueryRules',
    'slo',
    'cases',
    'observabilityCases',
    'generalCases',
]
