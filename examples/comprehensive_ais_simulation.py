#!/usr/bin/env python3
"""Comprehensive AIS and GPS simulation example."""

import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from simulator.core.enhanced_engine import EnhancedSimulationEngine, SimulationConfig
from simulator.core.trace_logger import create_trace_logger
from simulator.config.multi_vessel import (
    MultiVesselConfigManager, create_san_francisco_bay_scenario
)
from simulator.outputs.factory import OutputFactory
from nmea_lib.types import Position


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\nReceived interrupt signal. Stopping simulation...")
    global simulation_running
    simulation_running = False


def main():
    """Run comprehensive AIS simulation."""
    global simulation_running
    simulation_running = True
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 80)
    print("COMPREHENSIVE AIS & GPS SIMULATION")
    print("=" * 80)
    print()
    
    # Create simulation configuration
    config = SimulationConfig(
        time_factor=1.0,
        update_interval=1.0,
        duration=300,  # 5 minutes
        enable_gps=True,
        enable_ais=True,
        gps_update_interval=1.0,
        ais_update_interval=0.5,
        log_level="INFO",
        enable_trace_logging=True
    )
    
    print(f"Simulation Configuration:")
    print(f"  Duration: {config.duration} seconds")
    print(f"  GPS Updates: Every {config.gps_update_interval}s")
    print(f"  AIS Updates: Every {config.ais_update_interval}s")
    print(f"  Trace Logging: {'Enabled' if config.enable_trace_logging else 'Disabled'}")
    print()
    
    # Create enhanced simulation engine
    engine = EnhancedSimulationEngine(config)
    
    # Setup trace logging
    trace_logger = create_trace_logger(
        log_file="logs/ais_trace.jsonl",
        enable_console=False
    )
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    trace_logger.start()
    engine.set_trace_callback(trace_logger.log_message_generation)
    
    # Create configuration manager and load scenario
    config_manager = MultiVesselConfigManager()
    
    # Create San Francisco Bay scenario
    sf_scenario_config = create_san_francisco_bay_scenario()
    scenario = config_manager.create_fleet_scenario('sf_bay_demo', sf_scenario_config)
    
    print(f"Loaded Scenario: {scenario.name}")
    print(f"  Description: {scenario.description}")
    print(f"  Vessels: {len(scenario.vessels)}")
    print(f"  Base Stations: {len(scenario.base_stations)}")
    print()
    
    # Add vessels to simulation
    print("Adding vessels to simulation:")
    for vessel_config in scenario.vessels:
        mmsi = engine.add_vessel(vessel_config)
        pos = vessel_config['initial_position']
        print(f"  {vessel_config['name']} (MMSI: {mmsi}) at {pos['latitude']:.4f}, {pos['longitude']:.4f}")
    
    # Add base stations
    if scenario.base_stations:
        print("\\nAdding base stations:")
        for bs_config in scenario.base_stations:
            from nmea_lib.types.vessel import BaseStationData
            from datetime import datetime
            base_station = BaseStationData(
                mmsi=bs_config['mmsi'],
                position=Position(
                    bs_config['position']['latitude'],
                    bs_config['position']['longitude']
                ),
                timestamp=datetime.now()
            )
            engine.add_base_station(base_station)
            print(f"  {bs_config['name']} (MMSI: {bs_config['mmsi']})")
    
    print()
    
    # Setup output handlers
    output_configs = [
        {
            'type': 'file',
            'config': {
                'filename': 'logs/nmea_ais_output.log',
                'max_size_mb': 10,
                'backup_count': 3
            }
        },
        {
            'type': 'tcp',
            'config': {
                'host': '0.0.0.0',
                'port': 10110,
                'max_clients': 5
            }
        },
        {
            'type': 'udp',
            'config': {
                'host': '127.0.0.1',
                'port': 10111,
                'broadcast': True
            }
        }
    ]
    
    print("Setting up output handlers:")
    for output_config in output_configs:
        try:
            from simulator.config.parser import OutputConfig
            config_obj = OutputConfig(
                type=output_config['type'],
                enabled=True,
                config=output_config['config']
            )
            handler = OutputFactory.create_output_handler(config_obj)
            engine.add_output_handler(handler)
            print(f"  ✅ {output_config['type'].upper()}: {handler}")
        except Exception as e:
            print(f"  ❌ {output_config['type'].upper()}: {e}")
    
    print()
    
    # Start simulation
    print("Starting simulation...")
    engine.start()
    
    print("Simulation running. Press Ctrl+C to stop.")
    print()
    
    # Monitor simulation
    start_time = datetime.now()
    last_stats_time = start_time
    stats_interval = 30  # seconds
    
    try:
        while simulation_running and engine.is_running():
            time.sleep(1)
            
            current_time = datetime.now()
            
            # Print statistics periodically
            if (current_time - last_stats_time).total_seconds() >= stats_interval:
                stats = engine.get_statistics()
                trace_stats = trace_logger.get_statistics()
                
                print(f"\\n--- Statistics at {current_time.strftime('%H:%M:%S')} ---")
                print(f"Runtime: {stats['runtime_seconds']:.1f}s")
                print(f"Sentences sent: {stats['sentences_sent']} ({stats['sentences_per_second']:.1f}/s)")
                print(f"  GPS: {stats['gps_sentences']}")
                print(f"  AIS: {stats['ais_sentences']}")
                print(f"Active vessels: {stats['vessels_active']}")
                print(f"Errors: {stats['errors']}")
                print(f"Trace entries: {trace_stats['entries_logged']} ({trace_stats.get('entries_per_second', 0):.1f}/s)")
                
                # AIS scheduler statistics
                ais_stats = stats.get('ais_scheduler_stats', {})
                if ais_stats.get('message_types'):
                    print("AIS Message Types:")
                    for msg_type, type_stats in ais_stats['message_types'].items():
                        print(f"  Type {msg_type}: {type_stats['total_sent']} sent ({type_stats['description']})")
                
                print()
                last_stats_time = current_time
    
    except KeyboardInterrupt:
        print("\\nInterrupt received.")
    
    # Stop simulation
    print("Stopping simulation...")
    engine.stop()
    trace_logger.stop()
    
    # Final statistics
    final_stats = engine.get_statistics()
    final_trace_stats = trace_logger.get_statistics()
    
    print("\\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print(f"Total runtime: {final_stats['runtime_seconds']:.1f} seconds")
    print(f"Total sentences: {final_stats['sentences_sent']}")
    print(f"  GPS sentences: {final_stats['gps_sentences']}")
    print(f"  AIS sentences: {final_stats['ais_sentences']}")
    print(f"Average rate: {final_stats['sentences_per_second']:.1f} sentences/second")
    print(f"Errors: {final_stats['errors']}")
    print()
    print(f"Trace entries logged: {final_trace_stats['entries_logged']}")
    print(f"Trace entries dropped: {final_trace_stats['entries_dropped']}")
    print(f"Unique vessels traced: {final_trace_stats['vessels']}")
    print()
    
    # Show output files
    print("Output files generated:")
    output_files = [
        "logs/nmea_ais_output.log",
        "logs/ais_trace.jsonl"
    ]
    
    for file_path in output_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"  {file_path} ({size:,} bytes)")
        else:
            print(f"  {file_path} (not created)")
    
    print()
    print("Network endpoints:")
    print("  TCP: localhost:10110 (NMEA sentences)")
    print("  UDP: localhost:10111 (NMEA sentences)")
    print()
    print("To analyze trace data:")
    print("  python3 -c \"from simulator.core.trace_logger import analyze_trace_file; analyzer = analyze_trace_file('logs/ais_trace.jsonl'); print(analyzer.get_message_type_stats())\"")
    print()


if __name__ == "__main__":
    main()

