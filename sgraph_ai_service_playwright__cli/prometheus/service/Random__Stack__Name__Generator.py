# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Random__Stack__Name__Generator (prometheus-local copy)
# Generates "{adjective}-{scientist}" identifiers for sp prom stacks. Mirrors
# the elastic + opensearch + ec2 generators (same vocabulary by design — a
# future cleanup can promote one shared cli/aws version). Pure logic.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',
              'fast','fierce','fresh','grand','happy','keen','light','lucky',
              'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
              'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
              'maxwell','newton','noether','pascal','planck','turing','tesla',
              'volta','watt','wien','zeno']


class Random__Stack__Name__Generator(Type_Safe):

    def generate(self) -> str:                                                      # 'happy-turing' / 'bold-curie' / ...
        return f'{secrets.choice(ADJECTIVES)}-{secrets.choice(SCIENTISTS)}'
