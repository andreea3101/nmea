"""Date and time data types for NMEA sentences."""

from dataclasses import dataclass
from datetime import datetime, time, date
from typing import Optional
import re


@dataclass
class NMEATime:
    """Represents time in NMEA format (HHMMSS.SSS)."""
    
    hour: int
    minute: int
    second: int
    microsecond: int = 0
    
    def __post_init__(self):
        """Validate time components."""
        if not (0 <= self.hour <= 23):
            raise ValueError(f"Invalid hour: {self.hour}")
        if not (0 <= self.minute <= 59):
            raise ValueError(f"Invalid minute: {self.minute}")
        if not (0 <= self.second <= 59):
            raise ValueError(f"Invalid second: {self.second}")
        if not (0 <= self.microsecond <= 999999):
            raise ValueError(f"Invalid microsecond: {self.microsecond}")
    
    @classmethod
    def from_nmea(cls, time_str: str) -> 'NMEATime':
        """Parse NMEA time string (HHMMSS.SSS format)."""
        if not time_str:
            raise ValueError("Empty time string")
        
        # Match HHMMSS or HHMMSS.SSS format
        pattern = r'^(\d{2})(\d{2})(\d{2})(?:\.(\d{1,3}))?$'
        match = re.match(pattern, time_str)
        
        if not match:
            raise ValueError(f"Invalid NMEA time format: {time_str}")
        
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3))
        
        # Handle fractional seconds
        microsecond = 0
        if match.group(4):
            frac_str = match.group(4).ljust(6, '0')  # Pad to 6 digits
            microsecond = int(frac_str)
        
        return cls(hour, minute, second, microsecond)
    
    def to_nmea(self, include_fractional: bool = True) -> str:
        """Convert to NMEA time string format."""
        if include_fractional and self.microsecond > 0:
            frac = self.microsecond // 1000  # Convert to milliseconds
            return f"{self.hour:02d}{self.minute:02d}{self.second:02d}.{frac:03d}"
        else:
            return f"{self.hour:02d}{self.minute:02d}{self.second:02d}"
    
    @classmethod
    def from_datetime(cls, dt: datetime) -> 'NMEATime':
        """Create NMEATime from datetime object."""
        return cls(dt.hour, dt.minute, dt.second, dt.microsecond)
    
    def to_time(self) -> time:
        """Convert to Python time object."""
        return time(self.hour, self.minute, self.second, self.microsecond)
    
    @classmethod
    def now(cls) -> 'NMEATime':
        """Get current time as NMEATime."""
        return cls.from_datetime(datetime.utcnow())


@dataclass
class NMEADate:
    """Represents date in NMEA format (DDMMYY)."""
    
    day: int
    month: int
    year: int  # Full year (e.g., 2024)
    
    def __post_init__(self):
        """Validate date components."""
        if not (1 <= self.day <= 31):
            raise ValueError(f"Invalid day: {self.day}")
        if not (1 <= self.month <= 12):
            raise ValueError(f"Invalid month: {self.month}")
        if not (1900 <= self.year <= 2099):
            raise ValueError(f"Invalid year: {self.year}")
    
    @classmethod
    def from_nmea(cls, date_str: str) -> 'NMEADate':
        """Parse NMEA date string (DDMMYY format)."""
        if not date_str or len(date_str) != 6:
            raise ValueError(f"Invalid NMEA date format: {date_str}")
        
        try:
            day = int(date_str[:2])
            month = int(date_str[2:4])
            year_2digit = int(date_str[4:6])
            
            # Convert 2-digit year to 4-digit year
            # Assume 00-49 means 2000-2049, 50-99 means 1950-1999
            if year_2digit <= 49:
                year = 2000 + year_2digit
            else:
                year = 1900 + year_2digit
            
            return cls(day, month, year)
        except ValueError as e:
            raise ValueError(f"Invalid NMEA date format: {date_str}") from e
    
    def to_nmea(self) -> str:
        """Convert to NMEA date string format."""
        year_2digit = self.year % 100
        return f"{self.day:02d}{self.month:02d}{year_2digit:02d}"
    
    @classmethod
    def from_date(cls, d: date) -> 'NMEADate':
        """Create NMEADate from date object."""
        return cls(d.day, d.month, d.year)
    
    def to_date(self) -> date:
        """Convert to Python date object."""
        return date(self.year, self.month, self.day)
    
    @classmethod
    def today(cls) -> 'NMEADate':
        """Get current date as NMEADate."""
        return cls.from_date(date.today())


@dataclass
class NMEADateTime:
    """Combined date and time for NMEA sentences."""
    
    nmea_date: NMEADate
    nmea_time: NMEATime
    
    @classmethod
    def from_datetime(cls, dt: datetime) -> 'NMEADateTime':
        """Create from datetime object."""
        return cls(
            NMEADate.from_date(dt.date()),
            NMEATime.from_datetime(dt)
        )
    
    def to_datetime(self) -> datetime:
        """Convert to datetime object."""
        return datetime.combine(
            self.nmea_date.to_date(),
            self.nmea_time.to_time()
        )
    
    @classmethod
    def now(cls) -> 'NMEADateTime':
        """Get current date and time."""
        return cls.from_datetime(datetime.utcnow())

