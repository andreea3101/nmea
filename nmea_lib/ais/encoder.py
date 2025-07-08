"""6-bit ASCII encoding utilities for AIS messages."""

from typing import List
from nmea_lib.ais.constants import AIS_6BIT_ASCII, AIS_ASCII_6BIT


class AIS6BitEncoder:
    """Handles 6-bit ASCII encoding and decoding for AIS messages."""
    
    @staticmethod
    def encode_binary_to_6bit(binary_data: str) -> str:
        """Convert binary string to 6-bit ASCII encoded string."""
        # Ensure binary data length is multiple of 6
        while len(binary_data) % 6 != 0:
            binary_data += "0"
        
        encoded = ""
        for i in range(0, len(binary_data), 6):
            # Extract 6-bit chunk
            chunk = binary_data[i:i+6]
            # Convert to integer
            value = int(chunk, 2)
            # Map to 6-bit ASCII character
            encoded += AIS_6BIT_ASCII[value]
        
        return encoded
    
    @staticmethod
    def decode_6bit_to_binary(encoded_data: str) -> str:
        """Convert 6-bit ASCII encoded string back to binary."""
        binary = ""
        for char in encoded_data:
            if char in AIS_ASCII_6BIT:
                value = AIS_ASCII_6BIT[char]
                binary += format(value, '06b')
            else:
                # Invalid character, use 0
                binary += "000000"
        
        return binary
    
    @staticmethod
    def calculate_fill_bits(binary_length: int) -> int:
        """Calculate number of fill bits needed for 6-bit alignment."""
        remainder = binary_length % 6
        if remainder == 0:
            return 0
        return 6 - remainder
    
    @staticmethod
    def validate_6bit_string(encoded_data: str) -> bool:
        """Validate that all characters are valid 6-bit ASCII."""
        return all(char in AIS_ASCII_6BIT for char in encoded_data)


class AISMultiPartHandler:
    """Handles multi-part AIS message splitting and assembly."""
    
    @staticmethod
    def split_message(binary_data: str, max_chars_per_part: int = 56) -> List[str]:
        """Split long binary message into multiple parts."""
        # Calculate maximum bits per part (accounting for 6-bit encoding)
        max_bits_per_part = max_chars_per_part * 6
        
        parts = []
        for i in range(0, len(binary_data), max_bits_per_part):
            part = binary_data[i:i + max_bits_per_part]
            parts.append(part)
        
        return parts
    
    @staticmethod
    def needs_splitting(binary_data: str, max_chars: int = 56) -> bool:
        """Check if message needs to be split into multiple parts."""
        # Calculate encoded length
        fill_bits = AIS6BitEncoder.calculate_fill_bits(len(binary_data))
        total_bits = len(binary_data) + fill_bits
        encoded_chars = total_bits // 6
        
        return encoded_chars > max_chars
    
    @staticmethod
    def get_part_count(binary_data: str, max_chars_per_part: int = 56) -> int:
        """Get number of parts needed for message."""
        if not AISMultiPartHandler.needs_splitting(binary_data, max_chars_per_part):
            return 1
        
        max_bits_per_part = max_chars_per_part * 6
        return (len(binary_data) + max_bits_per_part - 1) // max_bits_per_part


# Test functions for validation
def test_6bit_encoding():
    """Test 6-bit encoding functionality."""
    # Test basic encoding
    test_binary = "000001000010000011"  # 1, 2, 3 in 6-bit
    encoded = AIS6BitEncoder.encode_binary_to_6bit(test_binary)
    expected = "123"  # Should map to characters 1, 2, 3
    print(f"Binary: {test_binary}")
    print(f"Encoded: {encoded}")
    print(f"Expected: {expected}")
    print(f"Match: {encoded == expected}")
    
    # Test decoding
    decoded = AIS6BitEncoder.decode_6bit_to_binary(encoded)
    print(f"Decoded: {decoded}")
    print(f"Original: {test_binary}")
    print(f"Match: {decoded.startswith(test_binary)}")
    
    # Test fill bits calculation
    for length in [1, 5, 6, 7, 11, 12, 18]:
        fill_bits = AIS6BitEncoder.calculate_fill_bits(length)
        print(f"Length {length}: {fill_bits} fill bits")


if __name__ == "__main__":
    test_6bit_encoding()

