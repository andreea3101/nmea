"""AIS trace logging system for detailed message analysis."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TextIO
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
from queue import Queue, Empty


@dataclass
class TraceEntry:
    """Single trace log entry."""
    timestamp: str
    event_type: str
    vessel_mmsi: int
    message_type: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    sentences: Optional[List[str]] = None
    input_data: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[float] = None
    errors: Optional[List[str]] = None


@dataclass
class LoggerState:
    """State of the AIS trace logger."""
    log_file: Optional[str] = None
    enable_console: bool = False
    max_queue_size: int = 10000
    log_queue: Queue = None
    running: bool = False
    log_thread: Optional[threading.Thread] = None
    file_handle: Optional[TextIO] = None

    def __post_init__(self):
        if self.log_queue is None:
            self.log_queue = Queue(maxsize=self.max_queue_size)


class AISTraceLogger:
    """Comprehensive trace logging for AIS message generation and processing."""

    def __init__(self, log_file: Optional[str] = None,
                 enable_console: bool = False,
                 max_queue_size: int = 10000):
        """Initialize AIS trace logger."""
        self.state: LoggerState = LoggerState(
            log_file=log_file,
            enable_console=enable_console,
            max_queue_size=max_queue_size
        )

        # Statistics
        self.stats = {
            'entries_logged': 0,
            'entries_dropped': 0,
            'start_time': None,
            'message_types': {},
            'vessels': set(),
            'errors': 0
        }

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.AISTraceLogger")
    
    def start(self):
        """Start the trace logging system."""
        if self.state.running:
            return

        self.state.running = True
        self.stats['start_time'] = datetime.now()

        # Open log file if specified
        if self.state.log_file:
            self.state.file_handle = open(self.state.log_file, 'w', encoding='utf-8')
            self.logger.info(f"Opened trace log file: {self.state.log_file}")

        # Start logging thread
        self.state.log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.state.log_thread.start()

        self.logger.info("AIS trace logger started")

    def stop(self):
        """Stop the trace logging system."""
        if not self.state.running:
            return

        self.state.running = False

        # Wait for log thread to finish
        if self.state.log_thread and self.state.log_thread.is_alive():
            self.state.log_thread.join(timeout=5.0)

        # Close file handle
        if self.state.file_handle:
            self.state.file_handle.close()
            self.state.file_handle = None

        self.logger.info("AIS trace logger stopped")
    
    def log_message_generation(self, vessel_mmsi: int, message_type: int,
                             sentences: List[str], input_data: Dict[str, Any],
                             processing_time_ms: float = None):
        """Log AIS message generation."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='message_generated',
            vessel_mmsi=vessel_mmsi,
            message_type=message_type,
            sentences=sentences,
            input_data=input_data,
            processing_time_ms=processing_time_ms
        )
        
        self._queue_entry(entry)
    
    def log_message_transmission(self, vessel_mmsi: int, message_type: int,
                               sentences: List[str], channel: str = None):
        """Log AIS message transmission."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='message_transmitted',
            vessel_mmsi=vessel_mmsi,
            message_type=message_type,
            sentences=sentences,
            data={'channel': channel} if channel else None
        )
        
        self._queue_entry(entry)
    
    def log_vessel_update(self, vessel_mmsi: int, position_data: Dict[str, Any]):
        """Log vessel position/state update."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='vessel_updated',
            vessel_mmsi=vessel_mmsi,
            data=position_data
        )
        
        self._queue_entry(entry)
    
    def log_scheduling_event(self, vessel_mmsi: int, message_type: int,
                           event_data: Dict[str, Any]):
        """Log AIS message scheduling event."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='message_scheduled',
            vessel_mmsi=vessel_mmsi,
            message_type=message_type,
            data=event_data
        )
        
        self._queue_entry(entry)
    
    def log_error(self, vessel_mmsi: int, error_message: str,
                  context: Optional[Dict[str, Any]] = None):
        """Log error event."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='error',
            vessel_mmsi=vessel_mmsi,
            errors=[error_message],
            data=context
        )
        
        self._queue_entry(entry)
        self.stats['errors'] += 1
    
    def log_binary_encoding(self, vessel_mmsi: int, message_type: int,
                          binary_data: str, encoded_payload: str,
                          encoding_details: Dict[str, Any]):
        """Log binary encoding process."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='binary_encoded',
            vessel_mmsi=vessel_mmsi,
            message_type=message_type,
            data={
                'binary_length': len(binary_data),
                'encoded_length': len(encoded_payload),
                'binary_data': binary_data[:100] + '...' if len(binary_data) > 100 else binary_data,
                'encoded_payload': encoded_payload,
                **encoding_details
            }
        )
        
        self._queue_entry(entry)
    
    def log_sentence_validation(self, sentence: str, is_valid: bool,
                              validation_errors: Optional[List[str]] = None):
        """Log sentence validation results."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type='sentence_validated',
            vessel_mmsi=0,  # Not vessel-specific
            data={
                'sentence': sentence,
                'is_valid': is_valid,
                'validation_errors': validation_errors or []
            }
        )
        
        self._queue_entry(entry)
    
    def _queue_entry(self, entry: TraceEntry):
        """Queue a trace entry for logging."""
        try:
            self.state.log_queue.put_nowait(entry)
        except:
            # Queue is full, drop the entry
            self.stats['entries_dropped'] += 1

    def _log_worker(self):
        """Worker thread for processing log entries."""
        while self.state.running or not self.state.log_queue.empty():
            try:
                # Get entry from queue with timeout
                entry = self.state.log_queue.get(timeout=1.0)
                self._write_entry(entry)
                self.state.log_queue.task_done()

            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in log worker: {e}")
    
    def _write_entry(self, entry: TraceEntry):
        """Write a single trace entry."""
        try:
            # Update statistics
            self.stats['entries_logged'] += 1
            self.stats['vessels'].add(entry.vessel_mmsi)

            if entry.message_type:
                msg_type = entry.message_type
                if msg_type not in self.stats['message_types']:
                    self.stats['message_types'][msg_type] = 0
                self.stats['message_types'][msg_type] += 1

            # Convert to JSON
            entry_dict = asdict(entry)
            json_line = json.dumps(entry_dict, separators=(',', ':'))

            # Write to file
            if self.state.file_handle:
                self.state.file_handle.write(json_line + '\n')
                self.state.file_handle.flush()

            # Write to console if enabled
            if self.state.enable_console:
                print(f"TRACE: {json_line}")

        except Exception as e:
            self.logger.error(f"Error writing trace entry: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trace logging statistics."""
        stats = self.stats.copy()
        stats['vessels'] = len(stats['vessels'])
        
        if stats['start_time']:
            runtime = (datetime.now() - stats['start_time']).total_seconds()
            stats['runtime_seconds'] = runtime
            stats['entries_per_second'] = stats['entries_logged'] / max(1, runtime)
        
        return stats
    
    def flush(self):
        """Flush any pending log entries."""
        if self.state.file_handle:
            self.state.file_handle.flush()


class TraceAnalyzer:
    """Analyzer for AIS trace logs."""
    
    def __init__(self, trace_file: str):
        """Initialize trace analyzer."""
        self.trace_file = trace_file
        self.entries: List[TraceEntry] = []
        self._load_entries()
    
    def _load_entries(self):
        """Load trace entries from file."""
        if not Path(self.trace_file).exists():
            raise FileNotFoundError(f"Trace file not found: {self.trace_file}")
        
        with open(self.trace_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    entry = TraceEntry(**data)
                    self.entries.append(entry)
                except Exception as e:
                    print(f"Error parsing line {line_num}: {e}")
    
    def get_vessel_messages(self, vessel_mmsi: int) -> List[TraceEntry]:
        """Get all messages for a specific vessel."""
        return [entry for entry in self.entries if entry.vessel_mmsi == vessel_mmsi]
    
    def get_message_type_stats(self) -> Dict[int, Dict[str, Any]]:
        """Get statistics by message type."""
        stats = {}
        
        for entry in self.entries:
            if entry.message_type and entry.event_type == 'message_generated':
                msg_type = entry.message_type
                if msg_type not in stats:
                    stats[msg_type] = {
                        'count': 0,
                        'vessels': set(),
                        'avg_processing_time': 0,
                        'total_processing_time': 0
                    }
                
                stats[msg_type]['count'] += 1
                stats[msg_type]['vessels'].add(entry.vessel_mmsi)
                
                if entry.processing_time_ms:
                    stats[msg_type]['total_processing_time'] += entry.processing_time_ms
        
        # Calculate averages
        for msg_type in stats:
            if stats[msg_type]['count'] > 0:
                stats[msg_type]['avg_processing_time'] = (
                    stats[msg_type]['total_processing_time'] / stats[msg_type]['count']
                )
            stats[msg_type]['vessels'] = len(stats[msg_type]['vessels'])
        
        return stats
    
    def get_vessel_timeline(self, vessel_mmsi: int) -> List[Dict[str, Any]]:
        """Get chronological timeline for a vessel."""
        vessel_entries = self.get_vessel_messages(vessel_mmsi)
        vessel_entries.sort(key=lambda x: x.timestamp)
        
        timeline = []
        for entry in vessel_entries:
            timeline.append({
                'timestamp': entry.timestamp,
                'event': entry.event_type,
                'message_type': entry.message_type,
                'data': entry.data
            })
        
        return timeline
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors."""
        error_entries = [entry for entry in self.entries if entry.event_type == 'error']
        
        error_summary = {
            'total_errors': len(error_entries),
            'vessels_with_errors': len(set(entry.vessel_mmsi for entry in error_entries)),
            'error_types': {},
            'recent_errors': []
        }
        
        for entry in error_entries:
            if entry.errors:
                for error in entry.errors:
                    if error not in error_summary['error_types']:
                        error_summary['error_types'][error] = 0
                    error_summary['error_types'][error] += 1
        
        # Get recent errors (last 10)
        recent_errors = sorted(error_entries, key=lambda x: x.timestamp, reverse=True)[:10]
        error_summary['recent_errors'] = [
            {
                'timestamp': entry.timestamp,
                'vessel_mmsi': entry.vessel_mmsi,
                'errors': entry.errors,
                'context': entry.data
            }
            for entry in recent_errors
        ]
        
        return error_summary
    
    def export_vessel_data(self, vessel_mmsi: int, output_file: str):
        """Export all data for a specific vessel."""
        vessel_data = {
            'vessel_mmsi': vessel_mmsi,
            'timeline': self.get_vessel_timeline(vessel_mmsi),
            'message_counts': {},
            'position_history': []
        }
        
        # Count messages by type
        for entry in self.get_vessel_messages(vessel_mmsi):
            if entry.message_type and entry.event_type == 'message_generated':
                msg_type = entry.message_type
                if msg_type not in vessel_data['message_counts']:
                    vessel_data['message_counts'][msg_type] = 0
                vessel_data['message_counts'][msg_type] += 1
            
            # Extract position data
            if entry.event_type == 'vessel_updated' and entry.data:
                position_data = {
                    'timestamp': entry.timestamp,
                    **entry.data
                }
                vessel_data['position_history'].append(position_data)
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(vessel_data, f, indent=2)


# Utility functions
def create_trace_logger(log_file: str = None, enable_console: bool = False) -> AISTraceLogger:
    """Create a new AIS trace logger."""
    return AISTraceLogger(log_file, enable_console)


def analyze_trace_file(trace_file: str) -> TraceAnalyzer:
    """Create a trace analyzer for a log file."""
    return TraceAnalyzer(trace_file)


def generate_trace_report(trace_file: str, output_file: str):
    """Generate a comprehensive trace report."""
    analyzer = TraceAnalyzer(trace_file)
    
    report = {
        'summary': {
            'total_entries': len(analyzer.entries),
            'unique_vessels': len(set(entry.vessel_mmsi for entry in analyzer.entries)),
            'time_range': {
                'start': min(entry.timestamp for entry in analyzer.entries) if analyzer.entries else None,
                'end': max(entry.timestamp for entry in analyzer.entries) if analyzer.entries else None
            }
        },
        'message_type_stats': analyzer.get_message_type_stats(),
        'error_summary': analyzer.get_error_summary(),
        'event_counts': {}
    }
    
    # Count events by type
    for entry in analyzer.entries:
        event_type = entry.event_type
        if event_type not in report['event_counts']:
            report['event_counts'][event_type] = 0
        report['event_counts'][event_type] += 1
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

