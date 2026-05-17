# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock model alias table (single source of truth)
#
# Maps short user-facing aliases to canonical Bedrock model IDs or
# cross-region inference profile ARNs.
#
# Single source of truth at runtime — no YAML / JSON file on disk. Previously
# loaded from library/reference/v0.2.29__bedrock-model-aliases.yaml via pyyaml,
# but that brought a transitive dependency we don't otherwise need; the table
# is small enough to live in Python.
#
# Cross-region inference profile ARNs use the form:
#   us.anthropic.claude-opus-4-5:0
#   eu.anthropic.claude-opus-4-5:0
# Application inference profiles use an ARN
# (arn:aws:bedrock:<region>::foundation-model/<id>).
#
# Bedrock__Model__Resolver selects the appropriate ID based on:
#   1. The user-supplied alias
#   2. The resolved AWS region (region_overrides take precedence)
#   3. Whether a cross-region profile is required for that alias+region pair
#
# IMPORTANT: model availability changes over time and by account/region.
# The `sg aws bedrock chat list-models` command reflects what is actually
# enabled in the account; this table is a static fallback reference only.
# ═══════════════════════════════════════════════════════════════════════════════


BEDROCK_MODEL_ALIASES = {
    'claude': {
        'default'    : 'anthropic.claude-3-5-haiku-20241022-v1:0',     # cheapest, fastest default
        'haiku-4.5'  : 'anthropic.claude-haiku-4-5:0'                ,
        'haiku-3.5'  : 'anthropic.claude-3-5-haiku-20241022-v1:0'    ,
        'haiku-3'    : 'anthropic.claude-3-haiku-20240307-v1:0'      ,
        'sonnet-4.6' : 'anthropic.claude-sonnet-4-6:0'               ,
        'sonnet-3.7' : 'anthropic.claude-3-7-sonnet-20250219-v1:0'   ,
        'sonnet-3.5' : 'anthropic.claude-3-5-sonnet-20241022-v2:0'   ,
        'sonnet-3'   : 'anthropic.claude-3-sonnet-20240229-v1:0'     ,
        'opus-4.7'   : 'us.anthropic.claude-opus-4-7:0'              ,    # cross-region profile — check region availability
        'opus-3'     : 'anthropic.claude-3-opus-20240229-v1:0'       ,
    },
    'nova': {
        'default' : 'amazon.nova-lite-v1:0'    ,                          # cheapest nova default
        'lite'    : 'amazon.nova-lite-v1:0'    ,
        'micro'   : 'amazon.nova-micro-v1:0'   ,
        'pro'     : 'amazon.nova-pro-v1:0'     ,
        'premier' : 'amazon.nova-premier-v1:0' ,
    },
    'llama': {
        'default'    : 'meta.llama3-8b-instruct-v1:0'              ,      # cheapest llama default
        '3.1'        : 'meta.llama3-1-8b-instruct-v1:0'            ,
        '3.2'        : 'meta.llama3-2-11b-instruct-v1:0'           ,
        '4-scout'    : 'meta.llama4-scout-17b-instruct-v1:0'       ,
        '4-maverick' : 'meta.llama4-maverick-17b-instruct-v1:0'    ,
    },
    'region_overrides': {
        'eu-west-1' : {
            'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0',                # EU profile when caller is in eu-west-1
        },
        'eu-west-2' : {
            'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0',
        },
        'eu-west-3' : {
            'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0',
        },
        'eu-central-1' : {
            'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0',
        },
        'eu-north-1' : {
            'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0',
        },
    },
}
