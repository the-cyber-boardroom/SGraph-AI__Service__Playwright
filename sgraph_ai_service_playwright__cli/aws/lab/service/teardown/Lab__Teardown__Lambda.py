# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Teardown__Lambda
# Stub — requires v2 vault-publish phase 2b (Lambda primitive expansion).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry  import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Phase__Not_Ready__Error import Lab__Phase__Not_Ready__Error


class Lab__Teardown__Lambda(Type_Safe):

    def teardown(self, entry: Schema__Lab__Ledger__Entry) -> bool:
        raise Lab__Phase__Not_Ready__Error(
            'Lambda teardown requires v2 phase 2b (sg aws lambda primitive expansion). Not yet available.'
        )
