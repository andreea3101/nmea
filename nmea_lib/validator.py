"""NMEA sentence validation utilities."""

import re
from typing import Optional


class SentenceValidator:
    """Validates NMEA sentence format and checksum."""
    
    # NMEA sentence pattern: $TALKERID,field1,field2,...*CHECKSUM\r\n
    NMEA_PATTERN = re.compile(r'^\$[A-Z]{2}[A-Z]{3},[^*]*\*[0-9A-F]{2}(?:\r\n|\r|\n)?$')
    
    @staticmethod
    def is_valid_format(sentence: str) -> bool:
        """Check if sentence matches NMEA format."""
        if not sentence:
            return False
        
        # Basic format check
        if not sentence.startswith('$'):
            return False
        
        if '*' not in sentence:
            return False
        
        # Length check (max 82 characters including CR/LF)
        if len(sentence) > 82:
            return False
        
        # Pattern match
        return bool(SentenceValidator.NMEA_PATTERN.match(sentence.upper()))
    
    @staticmethod
    def calculate_checksum(sentence_body: str) -> str:
        """Calculate NMEA checksum for sentence body (without $ and *)."""
        checksum = 0
        for char in sentence_body:
            checksum ^= ord(char)
        return f"{checksum:02X}"
    
    @staticmethod
    def validate_checksum(sentence: str) -> bool:
        """Validate NMEA sentence checksum."""
        if '*' not in sentence:
            return False
        
        try:
            # Split sentence and checksum
            sentence_part, checksum_part = sentence.split('*', 1)
            
            # Remove $ from beginning
            sentence_body = sentence_part[1:]
            
            # Extract checksum (remove any trailing CR/LF)
            checksum_str = checksum_part.rstrip('\r\n')
            
            if len(checksum_str) != 2:
                return False
            
            # Calculate expected checksum
            expected_checksum = SentenceValidator.calculate_checksum(sentence_body)
            
            # Compare checksums (case insensitive)
            return checksum_str.upper() == expected_checksum.upper()
            
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def is_valid(sentence: str) -> bool:
        """Perform complete validation of NMEA sentence."""
        return (SentenceValidator.is_valid_format(sentence) and 
                SentenceValidator.validate_checksum(sentence))
    
    @staticmethod
    def extract_talker_id(sentence: str) -> Optional[str]:
        """Extract talker ID from sentence."""
        if len(sentence) < 3 or not sentence.startswith('$'):
            return None
        return sentence[1:3]
    
    @staticmethod
    def extract_sentence_id(sentence: str) -> Optional[str]:
        """Extract sentence ID from sentence."""
        if len(sentence) < 6 or not sentence.startswith('$'):
            return None
        return sentence[3:6]
    
    @staticmethod
    def extract_fields(sentence: str) -> list[str]:
        """Extract data fields from sentence."""
        if '*' not in sentence:
            return []
        
        try:
            # Get everything between first comma and asterisk
            sentence_part = sentence.split('*')[0]
            
            # Find first comma (after sentence ID)
            comma_index = sentence_part.find(',')
            if comma_index == -1:
                return []
            
            # Split fields by comma
            fields_str = sentence_part[comma_index + 1:]
            return fields_str.split(',')
            
        except (ValueError, IndexError):
            return []

