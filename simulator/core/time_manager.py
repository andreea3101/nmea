"""Time management for NMEA simulation."""

import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class SimulationTime:
    """Represents simulation time state."""
    
    start_time: datetime
    current_time: datetime
    time_factor: float = 1.0  # Speed multiplier (1.0 = real-time)
    paused: bool = False
    
    def elapsed_seconds(self) -> float:
        """Get elapsed simulation time in seconds."""
        return (self.current_time - self.start_time).total_seconds()
    
    def elapsed_real_seconds(self) -> float:
        """Get elapsed real time in seconds."""
        return self.elapsed_seconds() / self.time_factor


class TimeManager:
    """Manages simulation time and timing control."""
    
    def __init__(self, start_time: Optional[datetime] = None, time_factor: float = 1.0):
        """
        Initialize time manager.
        
        Args:
            start_time: Simulation start time (defaults to current UTC time)
            time_factor: Time speed multiplier (1.0 = real-time, 2.0 = 2x speed)
        """
        self.start_time = start_time or datetime.utcnow()
        self.time_factor = max(0.1, time_factor)  # Minimum 0.1x speed
        self.paused = False
        
        # Real-time tracking
        self.real_start_time = time.time()
        self.pause_start_time: Optional[float] = None
        self.total_pause_time = 0.0
        
        # Current simulation time
        self.current_sim_time = self.start_time
    
    def get_current_time(self) -> datetime:
        """Get current simulation time."""
        if self.paused:
            return self.current_sim_time
        
        # Calculate elapsed real time (excluding pauses)
        current_real_time = time.time()
        elapsed_real = current_real_time - self.real_start_time - self.total_pause_time
        
        # Apply time factor to get simulation time
        elapsed_sim = elapsed_real * self.time_factor
        
        # Update current simulation time
        self.current_sim_time = self.start_time + timedelta(seconds=elapsed_sim)
        
        return self.current_sim_time
    
    def get_simulation_state(self) -> SimulationTime:
        """Get current simulation time state."""
        current_time = self.get_current_time()
        return SimulationTime(
            start_time=self.start_time,
            current_time=current_time,
            time_factor=self.time_factor,
            paused=self.paused
        )
    
    def pause(self) -> None:
        """Pause simulation time."""
        if not self.paused:
            self.paused = True
            self.pause_start_time = time.time()
    
    def resume(self) -> None:
        """Resume simulation time."""
        if self.paused and self.pause_start_time is not None:
            self.paused = False
            self.total_pause_time += time.time() - self.pause_start_time
            self.pause_start_time = None
    
    def set_time_factor(self, factor: float) -> None:
        """Set time speed multiplier."""
        if factor <= 0:
            raise ValueError("Time factor must be positive")
        
        # Update current time before changing factor
        self.get_current_time()
        
        # Reset timing with new factor
        self.time_factor = factor
        self.real_start_time = time.time()
        self.total_pause_time = 0.0
        self.start_time = self.current_sim_time
    
    def reset(self, start_time: Optional[datetime] = None) -> None:
        """Reset simulation time."""
        self.start_time = start_time or datetime.utcnow()
        self.current_sim_time = self.start_time
        self.real_start_time = time.time()
        self.total_pause_time = 0.0
        self.pause_start_time = None
        self.paused = False
    
    def sleep_until_next_update(self, update_interval: float) -> None:
        """Sleep until next update time in real-time."""
        if self.paused:
            time.sleep(0.1)  # Short sleep when paused
            return
        
        # Calculate sleep time based on time factor
        real_sleep_time = update_interval / self.time_factor
        
        # Minimum sleep time to prevent excessive CPU usage
        real_sleep_time = max(0.001, real_sleep_time)
        
        time.sleep(real_sleep_time)
    
    def format_time(self, dt: Optional[datetime] = None) -> str:
        """Format time for display."""
        if dt is None:
            dt = self.get_current_time()
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    def __str__(self) -> str:
        """String representation of time manager."""
        state = self.get_simulation_state()
        status = "PAUSED" if state.paused else "RUNNING"
        return (f"TimeManager({status}, "
                f"factor={state.time_factor:.1f}x, "
                f"time={self.format_time(state.current_time)})")

