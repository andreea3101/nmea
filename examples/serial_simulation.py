#!/usr/bin/env python3
"""Serial NMEA simulation example."""

import sys
import time
# import threading # Not needed for basic serial test client
# import socket # Not needed for serial
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.core.engine import SimulationEngine, SimulationConfig # Added SimulationConfig
from simulator.config.parser import ConfigParser # Still used for from_dict
from simulator.outputs.factory import OutputFactory
from nmea_lib import TalkerId # For SentenceConfig

# Guidance for setting up a virtual serial port pair:
# On Linux/macOS using socat:
# 1. Install socat: `sudo apt-get install socat` or `brew install socat`
# 2. Create a virtual serial port pair in your terminal:
#    socat -d -d pty,raw,echo=0,link=/tmp/vserial_sim_tx pty,raw,echo=0,link=/tmp/vserial_sim_rx
#    - This creates two linked pseudo-terminals:
#      - /tmp/vserial_sim_tx (simulator writes to this one)
#      - /tmp/vserial_sim_rx (you can read from this one, e.g., `cat /tmp/vserial_sim_rx`)
#    - Keep this socat command running in a separate terminal while you run the simulation.
# 3. Configure the `SERIAL_PORT_NAME` in this script to `/tmp/vserial_sim_tx`.
#
# On Windows:
# - You might need a virtual serial port emulator like `com0com`.
#   Setup a pair (e.g., COM10 and COM11) and configure SERIAL_PORT_NAME accordingly.

SERIAL_PORT_NAME = "/tmp/vserial_sim_tx" # Adjust if your virtual port is different

def create_serial_simulation_config() -> SimulationConfig:
    """Creates a simulation configuration focused on serial output."""

    # Basic simulation settings
    sim_config_dict = {
        'simulation': {
            'duration': 120,  # 2 minutes
            'time_factor': 1.0,
            'start_time': None
        },
        'vessel': {
            'name': "Serial Test Vessel",
            'initial_position': {'latitude': 37.7749, 'longitude': -122.4194},
            'initial_speed': 10.0,
            'initial_heading': 45.0
        },
        'movement': { # Optional, defaults will be used if omitted
            'speed_variation': 2.0,
            'course_variation': 10.0,
            'position_noise': 0.000005
        },
        'sentences': [
            {'type': 'GGA', 'talker_id': 'GP', 'rate': 1.0, 'enabled': True},
            {'type': 'RMC', 'talker_id': 'GP', 'rate': 1.0, 'enabled': True},
            {'type': 'VTG', 'talker_id': 'GP', 'rate': 2.0, 'enabled': True} # Example of another sentence
        ],
        'outputs': [
            {
                'type': 'serial',
                'enabled': True,
                'port': SERIAL_PORT_NAME,
                'baudrate': 9600,
                'timeout': 1.0, # Read timeout, not very relevant for output-only
                'write_timeout': 1.0,
                'line_ending': "\r\n",
                'max_reconnect_attempts': 3, # Try to reconnect a few times if port disappears
                'reconnect_delay': 5.0
            },
            { # Optional: also output to a file for easy inspection/debug
                'type': 'file',
                'enabled': True, # Set to false to disable
                'path': "nmea_serial_simulation_output.log",
                'append': False
            }
        ]
    }
    return ConfigParser.from_dict(sim_config_dict)


def main():
    """Run serial NMEA simulation example."""
    print("NMEA Simulator - Serial Example")
    print("=" * 50)
    print(f"INFO: This script will attempt to output NMEA data to serial port: {SERIAL_PORT_NAME}")
    print("INFO: Ensure a virtual serial port is set up (see comments in script) or a physical port is available.")
    print("INFO: To read the output, you can use 'cat /tmp/vserial_sim_rx' (if using socat example setup).")
    print("-" * 50)

    try:
        config = create_serial_simulation_config()
    except Exception as e:
        print(f"Failed to create configuration: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"Vessel: {config.vessel_name}")
    print(f"Initial position: {config.initial_latitude:.6f}, {config.initial_longitude:.6f}")
    print(f"Initial speed: {config.initial_speed} knots")
    print(f"Duration: {config.duration_seconds} seconds")
    print()

    # Create simulation engine
    engine = SimulationEngine(config)

    # Create output handlers from configuration
    if hasattr(config, 'output_configs'):
        output_handlers = OutputFactory.create_output_handlers(config.output_configs)
        if not output_handlers:
            print("Warning: No output handlers were created. Check configuration.")
            # return # Or continue if this is acceptable for some reason

        for handler in output_handlers:
            engine.add_output_handler(handler)
            print(f"Added output handler: {handler}")
    else:
        print("No output_configs attribute found in simulation configuration.")
        return

    print()

    # No client test threads for serial like in network_simulation.py
    # The "client" is an external program reading the other end of the serial port.

    try:
        print("Starting simulation...")
        engine.start()

        # Give the serial port a moment to initialize if needed
        time.sleep(1)

        # Monitor simulation
        start_time = time.time()
        while engine.running:
            time.sleep(10)  # Update every 10 seconds

            status = engine.get_status()
            elapsed = time.time() - start_time

            print(f"\n[{elapsed:6.1f}s] Simulation Status:")
            print(f"  Position: {status['position']['latitude']:.6f}, {status['position']['longitude']:.6f}")
            print(f"  Speed: {status['position']['speed_knots']:.1f} knots")
            print(f"  Heading: {status['position']['heading_degrees']:.1f}°")
            print(f"  Total sentences: {status['statistics']['total_sentences']}")

            # Show output handler status
            for i, handler_status in enumerate(status['output_handlers']):
                handler_info = "Unknown Handler"
                if 'port' in handler_status and 'baudrate' in handler_status : # Serial specific
                    handler_info = f"Serial ({handler_status['port']}@{handler_status['baudrate']})"
                elif 'server_address' in handler_status: # TCP
                    handler_info = f"TCP ({handler_status['server_address']})"
                elif 'targets' in handler_status: # UDP
                    handler_info = f"UDP (targets: {len(handler_status['targets'])})"
                elif 'file_path' in handler_status: # File
                    handler_info = f"File ({handler_status['file_path']})"

                print(f"  {handler_info}: {handler_status.get('sentences_sent', 0)} sent, Running: {handler_status.get('running', False)}")
                if 'is_open' in handler_status: # Serial specific
                    print(f"    Port Open: {handler_status['is_open']}, Reconnecting: {handler_status.get('reconnecting', False)}")

        print("\nSimulation completed!")

        # Show final statistics
        final_status = engine.get_status() # Get final status again after engine stop might update it
        stats = final_status['statistics']

        print(f"\nFinal Statistics:")
        print(f"  Total sentences generated: {stats['total_sentences']}")
        print(f"  Total runtime: {stats['runtime_seconds']:.1f} seconds")
        if stats['runtime_seconds'] > 0 :
            print(f"  Average rate: {stats['sentences_per_second']:.1f} sentences/second")
        print(f"  Sentences by type: {stats['sentences_by_type']}")

        # Log final status of output handlers
        if 'output_handlers' in final_status:
            print("\nFinal Output Handler Status:")
            for handler_status in final_status['output_handlers']:
                handler_info = "Unknown Handler"
                if 'port' in handler_status and 'baudrate' in handler_status :
                    handler_info = f"Serial ({handler_status['port']}@{handler_status['baudrate']})"
                elif 'file_path' in handler_status:
                     handler_info = f"File ({handler_status['file_path']})"

                print(f"  {handler_info}: Sent {handler_status.get('sentences_sent', 0)}, Running: {handler_status.get('running', False)}")
                if 'is_open' in handler_status:
                     print(f"    Port Open: {handler_status['is_open']}, Reconnecting: {handler_status.get('reconnecting', False)}")


    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")

    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("Stopping simulation...")
        engine.stop()
        print("Done.")


if __name__ == "__main__":
    main()
