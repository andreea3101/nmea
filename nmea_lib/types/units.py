"""Unit conversion and measurement data types for NMEA sentences."""

from dataclasses import dataclass
from enum import Enum


class SpeedUnit(Enum):
    """Speed unit enumeration."""

    KNOTS = "N"
    KMH = "K"
    MPH = "M"


class DistanceUnit(Enum):
    """Distance unit enumeration."""

    METERS = "M"
    FEET = "f"
    FATHOMS = "F"
    NAUTICAL_MILES = "N"


class BearingType(Enum):
    """Bearing type enumeration."""

    TRUE = "T"
    MAGNETIC = "M"


@dataclass
class Speed:
    """Represents speed with unit conversion capabilities."""

    value: float
    unit: SpeedUnit = SpeedUnit.KNOTS

    def __post_init__(self):
        """Validate speed value."""
        if self.value < 0:
            raise ValueError(f"Speed cannot be negative: {self.value}")

    def to_knots(self) -> float:
        """Convert speed to knots."""
        if self.unit == SpeedUnit.KNOTS:
            return self.value
        elif self.unit == SpeedUnit.KMH:
            return self.value * 0.539957
        elif self.unit == SpeedUnit.MPH:
            return self.value * 0.868976
        else:
            raise ValueError(f"Unknown speed unit: {self.unit}")

    def to_kmh(self) -> float:
        """Convert speed to km/h."""
        knots = self.to_knots()
        return knots * 1.852

    def to_mph(self) -> float:
        """Convert speed to mph."""
        knots = self.to_knots()
        return knots * 1.15078

    def convert_to(self, target_unit: SpeedUnit) -> "Speed":
        """Convert to target unit."""
        if target_unit == SpeedUnit.KNOTS:
            return Speed(self.to_knots(), target_unit)
        elif target_unit == SpeedUnit.KMH:
            return Speed(self.to_kmh(), target_unit)
        elif target_unit == SpeedUnit.MPH:
            return Speed(self.to_mph(), target_unit)
        else:
            raise ValueError(f"Unknown target unit: {target_unit}")

    def to_nmea(self) -> str:
        """Convert to NMEA format string."""
        return f"{self.value:.1f}"

    @classmethod
    def from_nmea(
            cls,
            value_str: str,
            unit: SpeedUnit = SpeedUnit.KNOTS) -> "Speed":
        """Create Speed from NMEA string."""
        if not value_str:
            return cls(0.0, unit)
        return cls(float(value_str), unit)


@dataclass
class Distance:
    """Represents distance with unit conversion capabilities."""

    value: float
    unit: DistanceUnit = DistanceUnit.METERS

    def __post_init__(self):
        """Validate distance value."""
        if self.value < 0:
            raise ValueError(f"Distance cannot be negative: {self.value}")

    def to_meters(self) -> float:
        """Convert distance to meters."""
        if self.unit == DistanceUnit.METERS:
            return self.value
        elif self.unit == DistanceUnit.FEET:
            return self.value * 0.3048
        elif self.unit == DistanceUnit.FATHOMS:
            return self.value * 1.8288
        elif self.unit == DistanceUnit.NAUTICAL_MILES:
            return self.value * 1852.0
        else:
            raise ValueError(f"Unknown distance unit: {self.unit}")

    def to_feet(self) -> float:
        """Convert distance to feet."""
        meters = self.to_meters()
        return meters * 3.28084

    def to_nautical_miles(self) -> float:
        """Convert distance to nautical miles."""
        meters = self.to_meters()
        return meters / 1852.0

    def convert_to(self, target_unit: DistanceUnit) -> "Distance":
        """Convert to target unit."""
        if target_unit == DistanceUnit.METERS:
            return Distance(self.to_meters(), target_unit)
        elif target_unit == DistanceUnit.FEET:
            return Distance(self.to_feet(), target_unit)
        elif target_unit == DistanceUnit.NAUTICAL_MILES:
            return Distance(self.to_nautical_miles(), target_unit)
        else:
            raise ValueError(f"Unknown target unit: {target_unit}")

    def to_nmea(self) -> str:
        """Convert to NMEA format string."""
        return f"{self.value:.1f}"

    @classmethod
    def from_nmea(
        cls, value_str: str, unit: DistanceUnit = DistanceUnit.METERS
    ) -> "Distance":
        """Create Distance from NMEA string."""
        if not value_str:
            return cls(0.0, unit)
        return cls(float(value_str), unit)


@dataclass
class Bearing:
    """Represents bearing/heading with type information."""

    value: float  # Degrees (0-360)
    bearing_type: BearingType = BearingType.TRUE

    def __post_init__(self):
        """Validate and normalize bearing value."""
        if not (0 <= self.value <= 360):
            # Normalize to 0-360 range
            self.value = self.value % 360

    def to_magnetic(self, magnetic_variation: float) -> "Bearing":
        """Convert true bearing to magnetic bearing."""
        if self.bearing_type == BearingType.MAGNETIC:
            return self

        # Subtract easterly variation, add westerly variation
        magnetic_value = (self.value - magnetic_variation) % 360
        return Bearing(magnetic_value, BearingType.MAGNETIC)

    def to_true(self, magnetic_variation: float) -> "Bearing":
        """Convert magnetic bearing to true bearing."""
        if self.bearing_type == BearingType.TRUE:
            return self

        # Add easterly variation, subtract westerly variation
        true_value = (self.value + magnetic_variation) % 360
        return Bearing(true_value, BearingType.TRUE)

    def to_nmea(self) -> str:
        """Convert to NMEA format string."""
        return f"{self.value:.1f}"

    @classmethod
    def from_nmea(
        cls, value_str: str, bearing_type: BearingType = BearingType.TRUE
    ) -> "Bearing":
        """Create Bearing from NMEA string."""
        if not value_str:
            return cls(0.0, bearing_type)
        return cls(float(value_str), bearing_type)

    def difference(self, other: "Bearing") -> float:
        """Calculate the shortest angular difference between two bearings."""
        diff = abs(self.value - other.value)
        return min(diff, 360 - diff)

    def __str__(self) -> str:
        """String representation of bearing."""
        type_str = "T" if self.bearing_type == BearingType.TRUE else "M"
        return f"{self.value:.1f}°{type_str}"
