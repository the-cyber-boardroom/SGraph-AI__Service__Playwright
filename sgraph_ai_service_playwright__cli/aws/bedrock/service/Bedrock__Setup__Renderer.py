# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Setup__Renderer
# Builds IAM policy JSON, console deeplinks, and guided setup steps for
# `sg aws bedrock setup`. Read-only — no AWS mutations.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Setup__Step import List__Schema__Bedrock__Setup__Step
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Setup__Step           import Schema__Bedrock__Setup__Step

_IAM_ACTIONS = [                                                                   # Minimum actions required for sg aws bedrock chat
    'bedrock:ListFoundationModels'              ,
    'bedrock:GetFoundationModel'                ,
    'bedrock:InvokeModel'                       ,
    'bedrock:InvokeModelWithResponseStream'     ,
]

_PROVIDER_RECOMMENDATIONS = {                                                      # Default model recommendations per provider
    'claude' : 'Anthropic Claude Haiku   (cheap; recommended default)',
    'nova'   : 'Amazon Nova Micro        (cheap; non-Anthropic option)',
    'llama'  : 'Meta Llama 3             (open-weights option)',
}


class Bedrock__Setup__Renderer(Type_Safe):

    def iam_policy_json(self, region: str = '') -> str:                           # Returns minimal IAM policy JSON string, pretty-printed
        policy = {
            'Version'  : '2012-10-17'   ,
            'Statement': [{
                'Sid'     : 'SgAwsBedrockChat' ,
                'Effect'  : 'Allow'            ,
                'Action'  : _IAM_ACTIONS       ,
                'Resource': '*'                ,
            }]
        }
        return json.dumps(policy, indent=2)

    def model_access_deeplink(self, region: str) -> str:                          # Returns AWS console deeplink for model access
        r = region or 'us-east-1'
        return (f'https://{r}.console.aws.amazon.com'
                f'/bedrock/home?region={r}#/modelaccess')

    def render_steps(self, region: str = '', providers: list = None) -> List__Schema__Bedrock__Setup__Step:
        if providers is None:
            providers = ['claude', 'nova']
        effective_region = region or 'us-east-1'
        steps            = List__Schema__Bedrock__Setup__Step()

        # ── Step 1: IAM permissions ───────────────────────────────────────────
        actions_block = '\n'.join(f'    {a}' for a in _IAM_ACTIONS)
        policy_json   = self.iam_policy_json(effective_region)
        step1_body    = (
            f'The active role needs these actions to use sg aws bedrock chat:\n'
            f'{actions_block}\n\n'
            f'Minimal policy JSON:\n{policy_json}\n\n'
            f'To attach to your role:\n'
            f'  aws iam put-role-policy \\\n'
            f'    --role-name <your-role> \\\n'
            f'    --policy-name SgAwsBedrockChat \\\n'
            f'    --policy-document file://<saved-snippet>.json'
        )
        steps.append(Schema__Bedrock__Setup__Step(step_no  = 1                   ,
                                                   title    = 'IAM permissions'  ,
                                                   body     = step1_body         ,
                                                   deeplink = ''                 ))

        # ── Step 2: Model access ──────────────────────────────────────────────
        rec_lines    = '\n'.join(
            f'  {_PROVIDER_RECOMMENDATIONS[p]}'
            for p in providers
            if p in _PROVIDER_RECOMMENDATIONS
        )
        deeplink     = self.model_access_deeplink(effective_region)
        step2_body   = (
            f'Bedrock requires explicit sign-up for each foundation model.\n\n'
            f'Enable at least:\n{rec_lines}\n\n'
            f'Console deeplink:\n  {deeplink}\n\n'
            f'Click "Manage model access" → select the models above → submit.\n'
            f'Approval is typically instant; some Anthropic models require a\n'
            f'one-time use-case justification.'
        )
        steps.append(Schema__Bedrock__Setup__Step(step_no  = 2                   ,
                                                   title    = 'Model access'     ,
                                                   body     = step2_body         ,
                                                   deeplink = deeplink           ))

        # ── Step 3: Verify ────────────────────────────────────────────────────
        step3_body = (
            f'After completing steps 1 and 2:\n'
            f'  sg aws bedrock check                  # all green\n'
            f'  sg aws bedrock chat claude --prompt "say ok"'
        )
        steps.append(Schema__Bedrock__Setup__Step(step_no  = 3                   ,
                                                   title    = 'Verify'           ,
                                                   body     = step3_body         ,
                                                   deeplink = ''                 ))
        return steps
