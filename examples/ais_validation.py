#!/usr/bin/env python3
"""AIS message validation and compliance testing."""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from nmea_lib.types import Position, create_vessel_state
from nmea_lib.types.vessel import VesselClass, ShipType, NavigationStatus
from nmea_lib.sentences.aivdm import AISMessageGenerator, validate_aivdm_sentence, extract_message_type
from nmea_lib.ais.encoder import AIS6BitEncoder


def test_message_type_1():
    """Test AIS Type 1 message generation and validation."""
    print("Testing AIS Type 1 (Position Report Class A):")
    
    # Create test vessel
    vessel = create_vessel_state(
        mmsi=227006760,
        vessel_name="TEST VESSEL 1",
        position=Position(37.7749, -122.4194),
        vessel_class=VesselClass.CLASS_A,
        sog=12.3,
        cog=89.0,
        heading=90,
        nav_status=NavigationStatus.UNDER_WAY_USING_ENGINE
    )
    
    generator = AISMessageGenerator()
    sentences, input_data = generator.generate_type_1(vessel)
    
    print(f"  Generated {len(sentences)} sentence(s)")
    for i, sentence in enumerate(sentences):
        print(f"    Sentence {i+1}: {sentence}")
        
        # Validate sentence
        is_valid = validate_aivdm_sentence(sentence)
        print(f"    Valid: {is_valid}")
        
        # Extract message type
        msg_type = extract_message_type(sentence)
        print(f"    Message Type: {msg_type}")
        
        # Check format compliance
        if sentence.startswith('!AIVDM,1,1,,A,') and sentence.count(',') == 6:
            print(f"    Format: ✅ Single-part AIVDM")
        else:
            print(f"    Format: ❌ Unexpected format")
    
    print(f"  Input data: {input_data}")
    print()


def test_message_type_5():
    """Test AIS Type 5 message generation and validation."""
    print("Testing AIS Type 5 (Static and Voyage Data):")
    
    # Create test vessel with voyage data
    vessel = create_vessel_state(
        mmsi=227006760,
        vessel_name="LONG VESSEL NAME TEST",
        position=Position(37.7749, -122.4194),
        vessel_class=VesselClass.CLASS_A,
        callsign="TEST123",
        ship_type=ShipType.CARGO_ALL_SHIPS
    )
    
    # Set voyage data
    vessel.voyage_data.destination = "SAN FRANCISCO"
    vessel.voyage_data.draught = 8.5
    
    generator = AISMessageGenerator()
    sentences, input_data = generator.generate_type_5(vessel)
    
    print(f"  Generated {len(sentences)} sentence(s)")
    for i, sentence in enumerate(sentences):
        print(f"    Sentence {i+1}: {sentence}")
        
        # Validate sentence
        is_valid = validate_aivdm_sentence(sentence)
        print(f"    Valid: {is_valid}")
        
        # Check multi-part format
        if '!AIVDM,2,' in sentence:
            print(f"    Format: ✅ Multi-part AIVDM")
        else:
            print(f"    Format: ❌ Expected multi-part")
    
    print(f"  Input data keys: {list(input_data.keys())}")
    print()


def test_message_type_18():
    """Test AIS Type 18 message generation and validation."""
    print("Testing AIS Type 18 (Class B Position Report):")
    
    # Create Class B vessel
    vessel = create_vessel_state(
        mmsi=227006760,
        vessel_name="CLASS B VESSEL",
        position=Position(37.7749, -122.4194),
        vessel_class=VesselClass.CLASS_B,
        sog=8.5,
        cog=45.0,
        heading=45
    )
    
    generator = AISMessageGenerator()
    sentences, input_data = generator.generate_type_18(vessel, channel='B')
    
    print(f"  Generated {len(sentences)} sentence(s)")
    for i, sentence in enumerate(sentences):
        print(f"    Sentence {i+1}: {sentence}")
        
        # Validate sentence
        is_valid = validate_aivdm_sentence(sentence)
        print(f"    Valid: {is_valid}")
        
        # Check channel
        if ',B,' in sentence:
            print(f"    Channel: ✅ Channel B")
        else:
            print(f"    Channel: ❌ Expected Channel B")
        
        # Extract message type
        msg_type = extract_message_type(sentence)
        print(f"    Message Type: {msg_type}")
    
    print(f"  Input data: {input_data}")
    print()


def test_6bit_encoding():
    """Test 6-bit ASCII encoding compliance."""
    print("Testing 6-bit ASCII Encoding:")
    
    # Test various binary patterns
    test_cases = [
        ("000001", "1"),  # Simple case
        ("000001000010000011", "123"),  # Multiple characters
        ("111111", "?"),  # Maximum value (63)
        ("000000", "0"),  # Minimum value (0)
    ]
    
    for binary, expected in test_cases:
        encoded = AIS6BitEncoder.encode_binary_to_6bit(binary)
        print(f"  Binary: {binary} -> Encoded: '{encoded}' (Expected: '{expected}')")
        
        if encoded == expected:
            print(f"    ✅ Correct")
        else:
            print(f"    ❌ Incorrect")
        
        # Test round-trip
        decoded = AIS6BitEncoder.decode_6bit_to_binary(encoded)
        if decoded.startswith(binary):
            print(f"    ✅ Round-trip successful")
        else:
            print(f"    ❌ Round-trip failed: {decoded}")
    
    print()


def test_nmea_sample_compliance():
    """Test compliance with nmea-sample format."""
    print("Testing NMEA Sample Format Compliance:")
    
    # Load reference sample if available
    sample_file = Path(__file__).parent.parent / "upload" / "nmea-sample"
    
    if sample_file.exists():
        print(f"  Loading reference samples from: {sample_file}")
        
        with open(sample_file, 'r') as f:
            lines = f.readlines()
        
        # Find AIVDM sentences
        aivdm_samples = [line.strip() for line in lines if line.startswith('!AIVDM')]
        
        print(f"  Found {len(aivdm_samples)} AIVDM sentences in reference")
        
        if aivdm_samples:
            # Test first few samples
            for i, sample in enumerate(aivdm_samples[:5]):
                print(f"    Sample {i+1}: {sample}")
                
                # Validate
                is_valid = validate_aivdm_sentence(sample)
                print(f"      Valid: {is_valid}")
                
                # Extract message type
                msg_type = extract_message_type(sample)
                print(f"      Message Type: {msg_type}")
                
                # Check format
                parts = sample.split(',')
                if len(parts) >= 7:
                    total_parts = parts[1]
                    part_num = parts[2]
                    channel = parts[4]
                    payload = parts[5]
                    fill_bits = parts[6].split('*')[0]
                    
                    print(f"      Parts: {part_num}/{total_parts}, Channel: {channel}, Payload: {len(payload)} chars, Fill: {fill_bits}")
                
                print()
    else:
        print(f"  ❌ Reference file not found: {sample_file}")
        print("  Generating our own samples for format validation...")
        
        # Generate our own samples and validate format
        vessel = create_vessel_state(
            mmsi=227006760,
            vessel_name="FORMAT TEST",
            position=Position(37.7749, -122.4194),
            vessel_class=VesselClass.CLASS_A
        )
        
        generator = AISMessageGenerator()
        
        # Test different message types
        test_types = [1, 5, 18]
        for msg_type in test_types:
            try:
                if msg_type == 18:
                    vessel.static_data.vessel_class = VesselClass.CLASS_B
                
                sentences, _ = generator.generate_message(msg_type, vessel)
                
                print(f"    Type {msg_type} format check:")
                for sentence in sentences:
                    print(f"      {sentence}")
                    
                    # Check NMEA format
                    if sentence.startswith('!AIVDM,') and '*' in sentence:
                        print(f"      ✅ Valid NMEA format")
                    else:
                        print(f"      ❌ Invalid NMEA format")
                
                print()
                
            except Exception as e:
                print(f"    ❌ Error generating Type {msg_type}: {e}")


def test_checksum_validation():
    """Test NMEA checksum validation."""
    print("Testing NMEA Checksum Validation:")
    
    # Test cases with known checksums
    test_sentences = [
        "!AIVDM,1,1,,A,13HOI:0P1kG?Vl@EWFk3NReh0000,0*75",  # Valid
        "!AIVDM,1,1,,A,13HOI:0P1kG?Vl@EWFk3NReh0000,0*76",  # Invalid checksum
        "!AIVDM,2,1,1,A,53HOI:000003BG?A59?BG?@3JG?>F`00000000160000040Hl0000000,0*69",  # Valid multi-part
    ]
    
    for sentence in test_sentences:
        print(f"  Testing: {sentence}")
        
        # Manual checksum calculation
        if '*' in sentence:
            body, checksum_part = sentence.split('*')
            body = body[1:]  # Remove '!'
            
            calculated_checksum = 0
            for char in body:
                calculated_checksum ^= ord(char)
            
            expected_checksum = checksum_part[:2]
            calculated_hex = f"{calculated_checksum:02X}"
            
            print(f"    Expected: {expected_checksum}, Calculated: {calculated_hex}")
            
            if expected_checksum.upper() == calculated_hex.upper():
                print(f"    ✅ Checksum valid")
            else:
                print(f"    ❌ Checksum invalid")
        
        # Validate using our function
        is_valid = validate_aivdm_sentence(sentence)
        print(f"    Validation result: {is_valid}")
        print()


def main():
    """Run all AIS validation tests."""
    print("=" * 80)
    print("AIS MESSAGE VALIDATION AND COMPLIANCE TESTING")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    test_message_type_1()
    test_message_type_5()
    test_message_type_18()
    test_6bit_encoding()
    test_checksum_validation()
    test_nmea_sample_compliance()
    
    print("=" * 80)
    print("VALIDATION TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

