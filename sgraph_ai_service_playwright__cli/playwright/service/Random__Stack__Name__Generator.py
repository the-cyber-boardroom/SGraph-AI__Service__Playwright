# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Random__Stack__Name__Generator (playwright-local copy)
# Generates "{adjective}-{scientist}" identifiers for sp playwright stacks.
# Vocabulary parity with vnc + elastic + os + prom.
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
