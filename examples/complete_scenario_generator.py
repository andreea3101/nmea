#!/usr/bin/env python3
"""
Complete NMEA Scenario Generator Example

This example demonstrates how to generate complete NMEA scenarios
exactly like the nmea-sample file, with reference data for decoder validation.
"""

import sys
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.generators.scenario_generator import (
    ScenarioGenerationConfig,
    generate_complete_scenario
)


def main():
    """Generate complete scenario with reference data."""
    
    print("=" * 80)
    print("COMPLETE NMEA SCENARIO GENERATOR")
    print("=" * 80)
    print()
    
    # Configuration options
    print("Choose scenario type:")
    print("1. Quick test (5 minutes, 3 vessels)")
    print("2. Standard scenario (30 minutes, 5 vessels)")
    print("3. Extended scenario (60 minutes, 8 vessels)")
    print("4. Custom configuration")
    
    try:
        choice = input("Enter choice (1-4) [default: 1]: ").strip() or "1"
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return
    
    # Create configuration based on choice
    if choice == "1":
        config = ScenarioGenerationConfig(
            start_time=datetime.now(),
            duration_minutes=5,
            output_dir="quick_test_scenario",
            vessel_count=3,
            time_step_seconds=1.0
        )
        print("\nGenerating quick test scenario...")
        
    elif choice == "2":
        config = ScenarioGenerationConfig(
            start_time=datetime.now(),
            duration_minutes=30,
            output_dir="standard_scenario",
            vessel_count=5,
            time_step_seconds=1.0
        )
        print("\nGenerating standard scenario...")
        
    elif choice == "3":
        config = ScenarioGenerationConfig(
            start_time=datetime.now(),
            duration_minutes=60,
            output_dir="extended_scenario",
            vessel_count=8,
            time_step_seconds=1.0
        )
        print("\nGenerating extended scenario...")
        
    elif choice == "4":
        print("\nCustom configuration:")
        try:
            duration = int(input("Duration in minutes [30]: ") or "30")
            vessel_count = int(input("Number of vessels [5]: ") or "5")
            output_dir = input("Output directory [custom_scenario]: ") or "custom_scenario"
            
            config = ScenarioGenerationConfig(
                start_time=datetime.now(),
                duration_minutes=duration,
                output_dir=output_dir,
                vessel_count=vessel_count,
                time_step_seconds=1.0
            )
            print(f"\nGenerating custom scenario ({duration} min, {vessel_count} vessels)...")
            
        except (ValueError, KeyboardInterrupt):
            print("Invalid input or cancelled. Using default configuration.")
            config = ScenarioGenerationConfig(
                start_time=datetime.now(),
                duration_minutes=30,
                output_dir="default_scenario",
                vessel_count=5
            )
    else:
        print("Invalid choice. Using default configuration.")
        config = ScenarioGenerationConfig(
            start_time=datetime.now(),
            duration_minutes=30,
            output_dir="default_scenario",
            vessel_count=5
        )
    
    print(f"Configuration:")
    print(f"  Duration: {config.duration_minutes} minutes")
    print(f"  Vessels: {config.vessel_count}")
    print(f"  Output directory: {config.output_dir}")
    print(f"  Start time: {config.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Generate scenario
    try:
        start_time = datetime.now()
        files = generate_complete_scenario(config)
        end_time = datetime.now()
        
        generation_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("SCENARIO GENERATION COMPLETE")
        print("=" * 80)
        print(f"Generation time: {generation_time:.1f} seconds")
        print()
        print("Generated files:")
        
        for file_type, file_path in files.items():
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            print(f"  {file_type:15}: {file_path} ({file_size:,} bytes)")
        
        print()
        print("File descriptions:")
        print("  nmea_file      : Raw NMEA sentences (like nmea-sample)")
        print("  reference_file : JSON with original data used to generate messages")
        print("  human_readable : Human-friendly explanation of each message")
        print("  csv_summary    : CSV format for spreadsheet analysis")
        print()
        
        # Show sample content
        nmea_file = files['nmea_file']
        if Path(nmea_file).exists():
            print("\nSample NMEA output (first 10 lines):")
            with open(nmea_file, 'r') as f:
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    print(f"  {line.strip()}")
            print()
        
        # Show statistics
        reference_file = files['reference_file']
        if Path(reference_file).exists():
            with open(reference_file, 'r') as f:
                data = json.load(f)
                stats = data.get('statistics', {})
                
                print("Generation statistics:")
                print(f"  Total messages: {stats.get('total_messages', 0):,}")
                print(f"  GPS messages: {stats.get('gps_messages', 0):,}")
                print(f"  AIS messages: {stats.get('ais_messages', 0):,}")
                
                msg_types = stats.get('message_types', {})
                if msg_types:
                    print("  AIS message types:")
                    for msg_type, count in sorted(msg_types.items()):
                        print(f"    Type {msg_type}: {count:,} messages")
        
        print()
        print("Usage for decoder validation:")
        print(f"1. Use '{nmea_file}' as input to your AIS decoder")
        print(f"2. Compare decoder output with '{files['reference_file']}'")
        print(f"3. Check '{files['human_readable']}' for detailed explanations")
        print()
        print("The reference file contains the exact input data used to generate")
        print("each AIS message, allowing you to verify your decoder's accuracy.")
        
    except Exception as e:
        print(f"\nError generating scenario: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
