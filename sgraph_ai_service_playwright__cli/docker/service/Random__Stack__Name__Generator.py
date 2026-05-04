# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Random__Stack__Name__Generator (docker-local copy)
# Generates "{adjective}-{scientist}" identifiers for sp docker stacks.
# Mirrors the linux + opensearch equivalents; each section is self-contained.
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

    def generate(self) -> str:
        return f'{secrets.choice(ADJECTIVES)}-{secrets.choice(SCIENTISTS)}'
