"""AIS message scheduler for managing transmission intervals."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from nmea_lib.ais.constants import AIS_MESSAGE_INTERVALS
from nmea_lib.types.vessel import VesselState, VesselClass


class MessagePriority(Enum):
    """Message transmission priority levels."""

    HIGH = 1  # Position reports (Types 1, 2, 3, 18)
    MEDIUM = 2  # Extended reports (Type 19)
    LOW = 3  # Static data (Types 5, 24)
    PERIODIC = 4  # Base station, aids to navigation (Types 4, 21)


@dataclass
class ScheduledMessage:
    """Represents a scheduled AIS message transmission."""

    message_type: int
    vessel_mmsi: int
    next_transmission: datetime
    interval: float  # seconds
    priority: MessagePriority
    last_sent: Optional[datetime] = None
    send_count: int = 0

    def is_due(self, current_time: datetime) -> bool:
        """Check if message is due for transmission."""
        return current_time >= self.next_transmission

    def mark_sent(self, sent_time: datetime):
        """Mark message as sent and schedule next transmission."""
        self.last_sent = sent_time
        self.send_count += 1
        self.next_transmission = sent_time + timedelta(seconds=self.interval)


@dataclass
class VesselSchedule:
    """Manages AIS message schedule for a single vessel."""

    vessel_mmsi: int
    vessel_class: VesselClass
    messages: Dict[int, ScheduledMessage] = field(default_factory=dict)

    def add_message_type(
        self,
        message_type: int,
        interval: float,
        priority: MessagePriority,
        start_time: datetime,
    ):
        """Add a message type to the schedule."""
        scheduled_msg = ScheduledMessage(
            message_type=message_type,
            vessel_mmsi=self.vessel_mmsi,
            next_transmission=start_time,
            interval=interval,
            priority=priority,
        )
        self.messages[message_type] = scheduled_msg

    def get_due_messages(
            self,
            current_time: datetime) -> List[ScheduledMessage]:
        """Get all messages due for transmission."""
        due_messages = []
        for msg in self.messages.values():
            if msg.is_due(current_time):
                due_messages.append(msg)

        # Sort by priority (high priority first)
        due_messages.sort(key=lambda x: x.priority.value)
        return due_messages

    def mark_message_sent(self, message_type: int, sent_time: datetime):
        """Mark a message type as sent."""
        if message_type in self.messages:
            self.messages[message_type].mark_sent(sent_time)

    def get_next_transmission_time(self) -> Optional[datetime]:
        """Get the next scheduled transmission time."""
        if not self.messages:
            return None

        next_times = [msg.next_transmission for msg in self.messages.values()]
        return min(next_times)


class AISMessageScheduler:
    """Manages AIS message transmission scheduling for multiple vessels."""

    def __init__(self):
        """Initialize AIS message scheduler."""
        self.vessel_schedules: Dict[int, VesselSchedule] = {}
        self.global_message_queue: List[ScheduledMessage] = []
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=5)

        # Message type configurations
        self.message_configs = self._create_message_configs()

    def _create_message_configs(self) -> Dict[int, Dict]:
        """Create message type configurations."""
        return {
            1: {
                "interval": 2.0,
                "priority": MessagePriority.HIGH,
                "vessel_classes": ["A"],
                "description": "Position Report Class A",
            },
            2: {
                "interval": 2.0,
                "priority": MessagePriority.HIGH,
                "vessel_classes": ["A"],
                "description": "Position Report Scheduled Class A",
            },
            3: {
                "interval": 2.0,
                "priority": MessagePriority.HIGH,
                "vessel_classes": ["A"],
                "description": "Position Report Response Class A",
            },
            4: {
                "interval": 10.0,
                "priority": MessagePriority.PERIODIC,
                "vessel_classes": ["BASE_STATION"],
                "description": "Base Station Report",
            },
            5: {
                "interval": 360.0,
                "priority": MessagePriority.LOW,
                "vessel_classes": ["A"],
                "description": "Static and Voyage Data",
            },
            18: {
                "interval": 3.0,
                "priority": MessagePriority.HIGH,
                "vessel_classes": ["B"],
                "description": "Position Report Class B",
            },
            19: {
                "interval": 30.0,
                "priority": MessagePriority.MEDIUM,
                "vessel_classes": ["B"],
                "description": "Extended Class B Report",
            },
            21: {
                "interval": 180.0,
                "priority": MessagePriority.PERIODIC,
                "vessel_classes": ["AID_NAV"],
                "description": "Aid-to-Navigation Report",
            },
            24: {
                "interval": 360.0,
                "priority": MessagePriority.LOW,
                "vessel_classes": ["B"],
                "description": "Static Data Report Class B",
            },
        }

    def add_vessel(
        self, vessel_state: VesselState, start_time: Optional[datetime] = None
    ):
        """Add a vessel to the scheduling system."""
        if start_time is None:
            start_time = datetime.now()

        mmsi = vessel_state.mmsi
        vessel_class = vessel_state.vessel_class

        # Create vessel schedule
        schedule = VesselSchedule(mmsi, vessel_class)

        # Add appropriate message types based on vessel class
        if vessel_class == VesselClass.CLASS_A:
            # Class A vessels send Types 1, 2, 3, 5
            schedule.add_message_type(
                1,
                self.message_configs[1]["interval"],
                MessagePriority.HIGH,
                start_time)
            schedule.add_message_type(
                5,
                self.message_configs[5]["interval"],
                MessagePriority.LOW,
                start_time + timedelta(seconds=30),
            )

            # Occasionally send Type 2 and 3 (scheduled and response)
            schedule.add_message_type(
                2,
                self.message_configs[2]["interval"] * 5,
                MessagePriority.HIGH,
                start_time + timedelta(seconds=10),
            )
            schedule.add_message_type(
                3,
                self.message_configs[3]["interval"] * 10,
                MessagePriority.HIGH,
                start_time + timedelta(seconds=20),
            )

        elif vessel_class == VesselClass.CLASS_B:
            # Class B vessels send Types 18, 19, 24
            schedule.add_message_type(
                18,
                self.message_configs[18]["interval"],
                MessagePriority.HIGH,
                start_time,
            )
            schedule.add_message_type(
                19,
                self.message_configs[19]["interval"],
                MessagePriority.MEDIUM,
                start_time + timedelta(seconds=15),
            )
            schedule.add_message_type(
                24,
                self.message_configs[24]["interval"],
                MessagePriority.LOW,
                start_time + timedelta(seconds=45),
            )

        self.vessel_schedules[mmsi] = schedule

    def add_base_station(
            self,
            mmsi: int,
            start_time: Optional[datetime] = None):
        """Add a base station to the scheduling system."""
        if start_time is None:
            start_time = datetime.now()

        schedule = VesselSchedule(
            mmsi, VesselClass.CLASS_A
        )  # Base stations use Class A format
        schedule.add_message_type(
            4,
            self.message_configs[4]["interval"],
            MessagePriority.PERIODIC,
            start_time)

        self.vessel_schedules[mmsi] = schedule

    def add_aid_to_navigation(
            self,
            mmsi: int,
            start_time: Optional[datetime] = None):
        """Add an aid to navigation to the scheduling system."""
        if start_time is None:
            start_time = datetime.now()

        schedule = VesselSchedule(
            mmsi, VesselClass.CLASS_A)  # AtoN use Class A format
        schedule.add_message_type(
            21,
            self.message_configs[21]["interval"],
            MessagePriority.PERIODIC,
            start_time,
        )

        self.vessel_schedules[mmsi] = schedule

    def get_due_messages(
        self, current_time: Optional[datetime] = None
    ) -> List[Tuple[int, int]]:
        """Get all messages due for transmission."""
        if current_time is None:
            current_time = datetime.now()

        due_messages = []

        for schedule in self.vessel_schedules.values():
            vessel_due = schedule.get_due_messages(current_time)
            for msg in vessel_due:
                due_messages.append((msg.vessel_mmsi, msg.message_type))

        return due_messages

    def mark_message_sent(
            self,
            vessel_mmsi: int,
            message_type: int,
            sent_time: Optional[datetime] = None):
        """Mark a message as sent."""
        if sent_time is None:
            sent_time = datetime.now()

        if vessel_mmsi in self.vessel_schedules:
            self.vessel_schedules[vessel_mmsi].mark_message_sent(
                message_type, sent_time
            )

    def get_vessel_schedule(
            self,
            vessel_mmsi: int) -> Optional[VesselSchedule]:
        """Get schedule for a specific vessel."""
        return self.vessel_schedules.get(vessel_mmsi)

    def remove_vessel(self, vessel_mmsi: int):
        """Remove a vessel from scheduling."""
        if vessel_mmsi in self.vessel_schedules:
            del self.vessel_schedules[vessel_mmsi]

    def get_next_transmission_time(self) -> Optional[datetime]:
        """Get the next scheduled transmission time across all vessels."""
        next_times = []

        for schedule in self.vessel_schedules.values():
            next_time = schedule.get_next_transmission_time()
            if next_time:
                next_times.append(next_time)

        return min(next_times) if next_times else None

    def get_transmission_statistics(self) -> Dict[str, any]:
        """Get transmission statistics."""
        stats = {
            "total_vessels": len(self.vessel_schedules),
            "vessel_classes": {},
            "message_types": {},
            "total_messages_sent": 0,
        }

        for schedule in self.vessel_schedules.values():
            # Count vessel classes
            vessel_class = schedule.vessel_class.value
            stats["vessel_classes"][vessel_class] = (
                stats["vessel_classes"].get(vessel_class, 0) + 1
            )

            # Count message types and sent messages
            for msg_type, msg in schedule.messages.items():
                if msg_type not in stats["message_types"]:
                    stats["message_types"][msg_type] = {
                        "count": 0,
                        "total_sent": 0,
                        "description": self.message_configs.get(
                            msg_type,
                            {}).get(
                            "description",
                            "Unknown"),
                    }

                stats["message_types"][msg_type]["count"] += 1
                stats["message_types"][msg_type]["total_sent"] += msg.send_count
                stats["total_messages_sent"] += msg.send_count

        return stats

    def cleanup_old_schedules(self, current_time: Optional[datetime] = None):
        """Clean up old or inactive schedules."""
        if current_time is None:
            current_time = datetime.now()

        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        # Remove schedules for vessels that haven't sent messages in a long
        # time
        inactive_threshold = timedelta(hours=1)
        inactive_vessels = []

        for mmsi, schedule in self.vessel_schedules.items():
            last_activity = None
            for msg in schedule.messages.values():
                if msg.last_sent and (
                    last_activity is None or msg.last_sent > last_activity
                ):
                    last_activity = msg.last_sent

            if last_activity and current_time - last_activity > inactive_threshold:
                inactive_vessels.append(mmsi)

        for mmsi in inactive_vessels:
            del self.vessel_schedules[mmsi]

        self.last_cleanup = current_time

    def update_vessel_intervals(self, vessel_mmsi: int, speed_knots: float):
        """Update message intervals based on vessel speed (dynamic intervals)."""
        if vessel_mmsi not in self.vessel_schedules:
            return

        schedule = self.vessel_schedules[vessel_mmsi]

        # Adjust position report intervals based on speed
        # Faster vessels report more frequently
        if 1 in schedule.messages:  # Type 1 - Class A position
            if speed_knots > 23:
                new_interval = 2.0  # High speed
            elif speed_knots > 14:
                new_interval = 6.0  # Medium speed
            elif speed_knots > 3:
                new_interval = 10.0  # Low speed
            else:
                new_interval = 10.0  # At anchor/moored

            schedule.messages[1].interval = new_interval

        if 18 in schedule.messages:  # Type 18 - Class B position
            if speed_knots > 14:
                new_interval = 5.0  # High speed
            elif speed_knots > 2:
                new_interval = 30.0  # Medium speed
            else:
                new_interval = 180.0  # Low speed/stationary

            schedule.messages[18].interval = new_interval

    def get_message_config(self, message_type: int) -> Optional[Dict]:
        """Get configuration for a message type."""
        return self.message_configs.get(message_type)

    def set_custom_interval(
            self,
            vessel_mmsi: int,
            message_type: int,
            interval: float):
        """Set custom interval for a specific vessel and message type."""
        if vessel_mmsi in self.vessel_schedules:
            schedule = self.vessel_schedules[vessel_mmsi]
            if message_type in schedule.messages:
                schedule.messages[message_type].interval = interval


# Utility functions for scheduler management
def create_default_scheduler() -> AISMessageScheduler:
    """Create a scheduler with default configuration."""
    return AISMessageScheduler()


def calculate_optimal_intervals(
    vessel_count: int, channel_capacity: float = 1000.0
) -> Dict[int, float]:
    """Calculate optimal message intervals based on vessel count and channel capacity."""
    # This is a simplified calculation - real AIS uses more complex algorithms
    base_intervals = AIS_MESSAGE_INTERVALS.copy()

    if vessel_count > 100:
        # Increase intervals for high vessel density
        scaling_factor = min(2.0, vessel_count / 100.0)
        for msg_type in base_intervals:
            base_intervals[msg_type] *= scaling_factor

    return base_intervals
