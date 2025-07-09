"""NMEA sentence implementations."""

from .gga import GGASentence
from .rmc import RMCSentence

# Register sentences with factory
from ..factory import SentenceFactory
from ..base import SentenceId

# Register implemented sentences
SentenceFactory.register_sentence(SentenceId.GGA, GGASentence)
SentenceFactory.register_sentence(SentenceId.RMC, RMCSentence)

__all__ = ["GGASentence", "RMCSentence"]
