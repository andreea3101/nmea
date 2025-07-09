"""Data types and utilities for NMEA sentence handling."""

from .position import Position, Hemisphere
from .datetime import NMEATime, NMEADate, NMEADateTime
from .units import Speed, Bearing, Distance, SpeedUnit, BearingType, DistanceUnit
from .enums import (
    CompassPoint,
    FaaMode,
    NavStatus,
    GsaMode,
    GsaFixType,
    DataStatus,
    ModeIndicator,
)
# Import GpsFixQuality and GpsFixStatus from base to re-export them via nmea_lib.types
from ..base import GpsFixQuality, GpsFixStatus
from .vessel import (
    VesselState,
    VesselStaticData,
    VesselNavigationData,
    VesselVoyageData,
    VesselDimensions,
    VesselETA,
    BaseStationData,
    AidToNavigationData,
    create_vessel_state,
    create_base_station,
    create_aid_to_navigation,
)

__all__ = [
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
    "GpsFixQuality",      # Added GpsFixQuality
    "GpsFixStatus",       # Added GpsFixStatus
    "CompassPoint",
    "FaaMode",
    "NavStatus",
    "GsaMode",
    "GsaFixType",
    "DataStatus",
    "ModeIndicator",
    "VesselState",
    "VesselStaticData",
    "VesselNavigationData",
    "VesselVoyageData",
    "VesselDimensions",
    "VesselETA",
    "BaseStationData",
    "AidToNavigationData",
    "create_vessel_state",
    "create_base_station",
    "create_aid_to_navigation",
]
