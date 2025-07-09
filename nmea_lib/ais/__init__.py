"""AIS (Automatic Identification System) support for NMEA 0183 simulator."""

from .constants import (
    AISMessageType,
    NavigationStatus,
    ShipType,
    EPFDType,
    AidType,
    VesselClass,
    AIS_MESSAGE_INTERVALS,
    AIS_MESSAGE_LENGTHS,
    AIS_6BIT_ASCII,
    AIS_ASCII_6BIT,
    MMSI_RANGES,
    AIS_CHANNELS,
    AIS_MAX_VALUES,
    AIS_NOT_AVAILABLE,
)

__all__ = [
    "AISMessageType",
    "NavigationStatus",
    "ShipType",
    "EPFDType",
    "AidType",
    "VesselClass",
    "AIS_MESSAGE_INTERVALS",
    "AIS_MESSAGE_LENGTHS",
    "AIS_6BIT_ASCII",
    "AIS_ASCII_6BIT",
    "MMSI_RANGES",
    "AIS_CHANNELS",
    "AIS_MAX_VALUES",
    "AIS_NOT_AVAILABLE",
]
