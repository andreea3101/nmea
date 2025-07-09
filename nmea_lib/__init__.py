"""Python NMEA 0183 Library."""

from .base import (
    Sentence,
    PositionSentence,
    TimeSentence,
    DateSentence,
    TalkerId,
    SentenceId,
    GpsFixQuality,  # GpsFixQuality is in base.py
    GpsFixStatus,   # GpsFixStatus is in base.py
)
from .types import (
    Position,
    Hemisphere,
    NMEATime,
    NMEADate,
    NMEADateTime,
    Speed,
    Bearing,
    Distance,
    SpeedUnit,
    BearingType,
    DistanceUnit,
    # Enums from types.enums that are re-exported by types/__init__.py
    # CompassPoint, FaaMode, NavStatus, GsaMode, GsaFixType, DataStatus, ModeIndicator
    # These are not directly listed in nmea_lib.__all__ but are part of nmea_lib.types.*
)
from .parser import SentenceParser, SentenceBuilder
from .validator import SentenceValidator
from .factory import SentenceFactory
from .sentences import GGASentence, RMCSentence

__version__ = "1.0.0"
__author__ = "NMEA Simulator Development Team"

__all__ = [
    # Base classes and enums
    "Sentence",
    "PositionSentence",
    "TimeSentence",
    "DateSentence",
    "TalkerId",
    "SentenceId",
    "GpsFixQuality",
    "GpsFixStatus",
    # Data types
    "Position",
    "Hemisphere",
    "NMEATime",
    "NMEADate",
    "NMEADateTime",
    "Speed",
    "Bearing",
    "Distance",
    "SpeedUnit",
    "BearingType",
    "DistanceUnit",
    # Parsing and validation
    "SentenceParser",
    "SentenceBuilder",
    "SentenceValidator",
    "SentenceFactory",
    # Sentence implementations
    "GGASentence",
    "RMCSentence",
]
