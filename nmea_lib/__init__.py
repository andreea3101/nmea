"""Python NMEA 0183 Library."""

from .base import *
from .types import *
from .parser import SentenceParser, SentenceBuilder
from .validator import SentenceValidator
from .factory import SentenceFactory
from .sentences import *

__version__ = "1.0.0"
__author__ = "NMEA Simulator Development Team"

__all__ = [
    # Base classes and enums
    'Sentence', 'PositionSentence', 'TimeSentence', 'DateSentence',
    'TalkerId', 'SentenceId', 'GpsFixQuality', 'GpsFixStatus',
    
    # Data types
    'Position', 'Hemisphere', 'NMEATime', 'NMEADate', 'NMEADateTime',
    'Speed', 'Bearing', 'Distance', 'SpeedUnit', 'BearingType', 'DistanceUnit',
    
    # Parsing and validation
    'SentenceParser', 'SentenceBuilder', 'SentenceValidator', 'SentenceFactory',
    
    # Sentence implementations
    'GGASentence', 'RMCSentence'
]

