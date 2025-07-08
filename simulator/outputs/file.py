"""File output handler for NMEA sentences."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO
from dataclasses import dataclass

from .base import OutputHandler


@dataclass
class FileOutputConfig:
    """Configuration for file output."""
    
    file_path: str
    append_mode: bool = True
    auto_flush: bool = True
    rotation_size_mb: Optional[int] = None  # Rotate when file exceeds size
    rotation_time_hours: Optional[int] = None  # Rotate every N hours
    max_files: int = 10  # Maximum number of rotated files to keep


class FileOutput(OutputHandler):
    """Outputs NMEA sentences to a file."""
    
    def __init__(self, config: FileOutputConfig):
        """Initialize file output handler."""
        super().__init__()
        self.config = config
        self.file_handle: Optional[TextIO] = None
        self.current_file_path = config.file_path
        self.bytes_written = 0
        self.file_start_time = datetime.now()
        
        # Ensure directory exists
        file_path = Path(config.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start file output."""
        if self.is_running:
            return
        
        try:
            mode = 'a' if self.config.append_mode else 'w'
            self.file_handle = open(self.config.file_path, mode, encoding='utf-8')
            
            # Get current file size if appending
            if self.config.append_mode:
                self.bytes_written = self.file_handle.tell()
            else:
                self.bytes_written = 0
            
            self.file_start_time = datetime.now()
            self.is_running = True
            
            # Write header comment
            if not self.config.append_mode or self.bytes_written == 0:
                header = f"# NMEA Simulation started at {self.file_start_time.isoformat()}\n"
                self.file_handle.write(header)
                self.bytes_written += len(header.encode('utf-8'))
            
        except Exception as e:
            raise RuntimeError(f"Failed to start file output: {e}")
    
    def stop(self) -> None:
        """Stop file output."""
        if not self.is_running:
            return
        
        try:
            if self.file_handle:
                # Write footer comment
                footer = f"# NMEA Simulation ended at {datetime.now().isoformat()}\n"
                self.file_handle.write(footer)
                
                self.file_handle.close()
                self.file_handle = None
            
            self.is_running = False
            
        except Exception as e:
            print(f"Warning: Error stopping file output: {e}")
    
    def send_sentence(self, sentence: str) -> bool:
        """Send NMEA sentence to file."""
        if not self.is_running or not self.file_handle:
            return False
        
        try:
            # Check if rotation is needed
            self._check_rotation()
            
            # Write sentence
            self.file_handle.write(sentence)
            sentence_bytes = len(sentence.encode('utf-8'))
            self.bytes_written += sentence_bytes
            
            # Auto-flush if enabled
            if self.config.auto_flush:
                self.file_handle.flush()
            
            self.sentences_sent += 1
            return True
            
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False
    
    def _check_rotation(self) -> None:
        """Check if file rotation is needed."""
        needs_rotation = False
        
        # Check size-based rotation
        if (self.config.rotation_size_mb and 
            self.bytes_written > self.config.rotation_size_mb * 1024 * 1024):
            needs_rotation = True
        
        # Check time-based rotation
        if (self.config.rotation_time_hours and
            (datetime.now() - self.file_start_time).total_seconds() > 
            self.config.rotation_time_hours * 3600):
            needs_rotation = True
        
        if needs_rotation:
            self._rotate_file()
    
    def _rotate_file(self) -> None:
        """Rotate the current file."""
        if not self.file_handle:
            return
        
        try:
            # Close current file
            self.file_handle.close()
            
            # Generate rotated filename
            base_path = Path(self.config.file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{base_path.stem}_{timestamp}{base_path.suffix}"
            rotated_path = base_path.parent / rotated_name
            
            # Rename current file
            os.rename(self.config.file_path, rotated_path)
            
            # Clean up old files
            self._cleanup_old_files()
            
            # Open new file
            self.file_handle = open(self.config.file_path, 'w', encoding='utf-8')
            self.bytes_written = 0
            self.file_start_time = datetime.now()
            
            # Write header
            header = f"# NMEA Simulation continued at {self.file_start_time.isoformat()}\n"
            self.file_handle.write(header)
            self.bytes_written += len(header.encode('utf-8'))
            
        except Exception as e:
            print(f"Error rotating file: {e}")
            # Try to reopen original file
            try:
                self.file_handle = open(self.config.file_path, 'a', encoding='utf-8')
            except Exception:
                self.is_running = False
    
    def _cleanup_old_files(self) -> None:
        """Clean up old rotated files."""
        try:
            base_path = Path(self.config.file_path)
            pattern = f"{base_path.stem}_*{base_path.suffix}"
            
            # Find all rotated files
            rotated_files = list(base_path.parent.glob(pattern))
            
            # Sort by modification time (newest first)
            rotated_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove excess files
            for old_file in rotated_files[self.config.max_files:]:
                try:
                    old_file.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete old file {old_file}: {e}")
                    
        except Exception as e:
            print(f"Warning: Error cleaning up old files: {e}")
    
    def get_status(self) -> dict:
        """Get output handler status."""
        status = super().get_status()
        status.update({
            'file_path': self.config.file_path,
            'bytes_written': self.bytes_written,
            'file_size_mb': self.bytes_written / (1024 * 1024),
            'file_exists': os.path.exists(self.config.file_path)
        })
        return status
    
    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.is_running else "STOPPED"
        size_mb = self.bytes_written / (1024 * 1024)
        return f"FileOutput({status}, {self.config.file_path}, {size_mb:.1f}MB, {self.sentences_sent} sentences)"

