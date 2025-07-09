"""NMEA sentence factory for creating sentence objects."""

from typing import Dict, Type, Optional
from .base import Sentence, SentenceId, TalkerId
from .parser import SentenceParser


class SentenceFactory:
    """Factory for creating NMEA sentence objects."""

    # Registry of sentence classes
    _sentence_classes: Dict[SentenceId, Type[Sentence]] = {}

    @classmethod
    def register_sentence(
        cls, sentence_id: SentenceId, sentence_class: Type[Sentence]
    ) -> None:
        """Register a sentence class for a specific sentence ID."""
        cls._sentence_classes[sentence_id] = sentence_class

    @classmethod
    def create_sentence(cls, nmea_string: str) -> Optional[Sentence]:
        """Create a sentence object from NMEA string."""
        try:
            parser = SentenceParser(nmea_string)

            if not parser.is_valid() or not parser.sentence_id:
                return None

            sentence_class = cls._sentence_classes.get(parser.sentence_id)
            if not sentence_class:
                raise ValueError(
                    f"Unsupported sentence type: {
                        parser.sentence_id}"
                )

            return sentence_class.from_sentence(nmea_string)

        except (ValueError, Exception):
            return None

    @classmethod
    def create_empty_sentence(
        cls, talker_id: TalkerId, sentence_id: SentenceId
    ) -> Optional[Sentence]:
        """Create an empty sentence object for building."""
        sentence_class = cls._sentence_classes.get(sentence_id)
        if not sentence_class:
            return None

        # Create instance with empty data
        return sentence_class(talker_id, sentence_id)

    @classmethod
    def get_supported_sentences(cls) -> list[SentenceId]:
        """Get list of supported sentence types."""
        return list(cls._sentence_classes.keys())

    @classmethod
    def is_supported(cls, sentence_id: SentenceId) -> bool:
        """Check if sentence type is supported."""
        return sentence_id in cls._sentence_classes
