# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Stack__Name__Generator
# Generates memorable adjective-scientist names for stack instances.
# ═══════════════════════════════════════════════════════════════════════════════

import random

from osbot_utils.type_safe.Type_Safe import Type_Safe

ADJECTIVES = ['brave', 'calm', 'clean', 'clever', 'cool', 'crisp', 'deft',
              'eager', 'fair', 'fast', 'firm', 'fresh', 'keen', 'kind',
              'lean', 'light', 'neat', 'nimble', 'quick', 'quiet', 'sharp',
              'sleek', 'smart', 'smooth', 'steady', 'still', 'swift', 'warm']

SCIENTISTS = ['bohr', 'curie', 'darwin', 'einstein', 'euler', 'faraday',
              'fermi', 'feynman', 'gauss', 'heisenberg', 'hopper', 'hubble',
              'lovelace', 'maxwell', 'mendel', 'newton', 'pascal', 'pauli',
              'planck', 'turing', 'volta', 'watt']


class Stack__Name__Generator(Type_Safe):

    def generate(self) -> str:
        return f'{random.choice(ADJECTIVES)}-{random.choice(SCIENTISTS)}'
