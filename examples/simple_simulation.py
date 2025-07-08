#!/usr/bin/env python3
"""Simple NMEA simulation example."""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.core.engine import SimulationEngine
from simulator.config.parser import SimulatorConfig
from simulator.outputs.file import FileOutput, FileOutputConfig


def main():
    """Run simple NMEA simulation."""
    print("NMEA Simulator - Simple Example")
    print("=" * 40)
    
    # Create configuration
    config = SimulatorConfig.create_example()
    config.duration_seconds = 60  # 1 minute simulation
    config.initial_speed = 5.0  # 5 knots
    
    print(f"Vessel: {config.vessel_name}")
    print(f"Initial position: {config.initial_latitude:.6f}, {config.initial_longitude:.6f}")
    print(f"Initial speed: {config.initial_speed} knots")
    print(f"Duration: {config.duration_seconds} seconds")
    print()
    
    # Create simulation engine
    engine = SimulationEngine(config)
    
    # Add file output
    output_config = FileOutputConfig(
        file_path="nmea_output.log",
        append_mode=False,  # Overwrite existing file
        auto_flush=True
    )
    file_output = FileOutput(output_config)
    engine.add_output_handler(file_output)
    
    try:
        print("Starting simulation...")
        engine.start()
        
        # Monitor simulation
        start_time = time.time()
        while engine.running:
            time.sleep(5)  # Update every 5 seconds
            
            status = engine.get_status()
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:6.1f}s] "
                  f"Pos: {status['position']['latitude']:.6f}, {status['position']['longitude']:.6f} "
                  f"Speed: {status['position']['speed_knots']:.1f}kts "
                  f"Heading: {status['position']['heading_degrees']:.1f}° "
                  f"Sentences: {status['statistics']['total_sentences']}")
        
        print("\nSimulation completed!")
        
        # Show final statistics
        final_status = engine.get_status()
        stats = final_status['statistics']
        
        print(f"\nFinal Statistics:")
        print(f"  Total sentences: {stats['total_sentences']}")
        print(f"  Runtime: {stats['runtime_seconds']:.1f} seconds")
        print(f"  Rate: {stats['sentences_per_second']:.1f} sentences/second")
        print(f"  Sentences by type: {stats['sentences_by_type']}")
        
        # Show output file info
        if Path("nmea_output.log").exists():
            file_size = Path("nmea_output.log").stat().st_size
            print(f"  Output file: nmea_output.log ({file_size} bytes)")
        
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    
    except Exception as e:
        print(f"Error during simulation: {e}")
    
    finally:
        print("Stopping simulation...")
        engine.stop()
        print("Done.")


if __name__ == "__main__":
    main()

