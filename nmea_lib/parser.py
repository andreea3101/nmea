"""NMEA sentence parsing utilities."""

from typing import List, Optional, Union, Type
from .base import Sentence, TalkerId, SentenceId, ParsedSentence
from .validator import SentenceValidator


class SentenceParser:
    """Base parser for NMEA sentences with common functionality."""
    
    def __init__(self, sentence: str):
        """Initialize parser with NMEA sentence string."""
        self.raw_sentence = sentence.strip()
        self.parsed_data: Optional[ParsedSentence] = None
        self._parse()
    
    def _parse(self) -> None:
        """Parse the NMEA sentence into components."""
        if not SentenceValidator.is_valid(self.raw_sentence):
            raise ValueError(f"Invalid NMEA sentence: {self.raw_sentence}")
        
        # Extract components
        talker_str = SentenceValidator.extract_talker_id(self.raw_sentence)
        sentence_str = SentenceValidator.extract_sentence_id(self.raw_sentence)
        fields = SentenceValidator.extract_fields(self.raw_sentence)
        
        if not talker_str or not sentence_str:
            raise ValueError(f"Cannot parse sentence components: {self.raw_sentence}")
        
        # Extract checksum
        checksum_part = self.raw_sentence.split('*')[1]
        checksum = checksum_part.rstrip('\r\n')
        
        # Create parsed data
        try:
            talker_id = TalkerId.parse(self.raw_sentence)
            sentence_id = SentenceId.parse(self.raw_sentence)
        except ValueError as e:
            raise ValueError(f"Unsupported sentence type: {talker_str}{sentence_str}") from e
        
        self.parsed_data = ParsedSentence(
            talker_id=talker_id,
            sentence_id=sentence_id,
            fields=fields,
            checksum=checksum,
            raw_sentence=self.raw_sentence
        )
    
    def get_field(self, index: int) -> str:
        """Get field value by index."""
        if not self.parsed_data or index >= len(self.parsed_data.fields):
            return ""
        return self.parsed_data.fields[index]
    
    def get_int_field(self, index: int) -> Optional[int]:
        """Get field value as integer."""
        field_value = self.get_field(index)
        if not field_value:
            return None
        try:
            return int(field_value)
        except ValueError:
            return None
    
    def get_float_field(self, index: int) -> Optional[float]:
        """Get field value as float."""
        field_value = self.get_field(index)
        if not field_value:
            return None
        try:
            return float(field_value)
        except ValueError:
            return None
    
    def set_field(self, index: int, value: str) -> None:
        """Set field value by index."""
        if not self.parsed_data:
            return
        
        # Extend fields list if necessary
        while len(self.parsed_data.fields) <= index:
            self.parsed_data.fields.append("")
        
        self.parsed_data.fields[index] = str(value) if value is not None else ""
    
    def set_int_field(self, index: int, value: Optional[int]) -> None:
        """Set field value as integer."""
        if value is not None:
            self.set_field(index, str(value))
        else:
            self.set_field(index, "")
    
    def set_float_field(self, index: int, value: Optional[float], precision: int = 1) -> None:
        """Set field value as float with specified precision."""
        if value is not None:
            format_str = f"{{:.{precision}f}}"
            self.set_field(index, format_str.format(value))
        else:
            self.set_field(index, "")
    
    def build_sentence(self) -> str:
        """Build NMEA sentence string from parsed data."""
        if not self.parsed_data:
            raise ValueError("No parsed data available")
        
        # Build sentence header
        header = f"${self.parsed_data.talker_id.value}{self.parsed_data.sentence_id.value}"
        
        # Build fields string
        fields_str = ",".join(self.parsed_data.fields)
        
        # Build sentence body (without checksum)
        sentence_body = f"{self.parsed_data.talker_id.value}{self.parsed_data.sentence_id.value},{fields_str}"
        
        # Calculate checksum
        checksum = SentenceValidator.calculate_checksum(sentence_body)
        
        # Build complete sentence
        return f"{header},{fields_str}*{checksum}\r\n"
    
    @property
    def talker_id(self) -> Optional[TalkerId]:
        """Get talker ID."""
        return self.parsed_data.talker_id if self.parsed_data else None
    
    @property
    def sentence_id(self) -> Optional[SentenceId]:
        """Get sentence ID."""
        return self.parsed_data.sentence_id if self.parsed_data else None
    
    @property
    def fields(self) -> List[str]:
        """Get all fields."""
        return self.parsed_data.fields if self.parsed_data else []
    
    @property
    def field_count(self) -> int:
        """Get number of fields."""
        return len(self.fields)
    
    def is_valid(self) -> bool:
        """Check if parsed sentence is valid."""
        return self.parsed_data is not None and self.parsed_data.is_valid()


class SentenceBuilder:
    """Builder for creating NMEA sentences."""
    
    def __init__(self, talker_id: TalkerId, sentence_id: SentenceId):
        """Initialize builder with sentence identifiers."""
        self.talker_id = talker_id
        self.sentence_id = sentence_id
        self.fields: List[str] = []
    
    def add_field(self, value: Union[str, int, float, None]) -> 'SentenceBuilder':
        """Add a field to the sentence."""
        if value is None:
            self.fields.append("")
        else:
            self.fields.append(str(value))
        return self
    
    def add_float_field(self, value: Optional[float], precision: int = 1) -> 'SentenceBuilder':
        """Add a float field with specified precision."""
        if value is not None:
            format_str = f"{{:.{precision}f}}"
            self.fields.append(format_str.format(value))
        else:
            self.fields.append("")
        return self
    
    def build(self) -> str:
        """Build the complete NMEA sentence."""
        # Build sentence body
        sentence_body = f"{self.talker_id.value}{self.sentence_id.value},{','.join(self.fields)}"
        
        # Calculate checksum
        checksum = SentenceValidator.calculate_checksum(sentence_body)
        
        # Build complete sentence
        return f"${sentence_body}*{checksum}\r\n"

