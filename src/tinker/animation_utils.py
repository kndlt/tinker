"""Simple animation utilities for terminal output"""

import time
import sys
import threading
from typing import Optional


class SimpleSpinner:
    """A simple spinner animation for terminal output"""
    
    def __init__(self, message: str = "Processing"):
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.is_spinning = False
        self.thread: Optional[threading.Thread] = None
    
    def _spin(self):
        """Internal spinning method"""
        i = 0
        while self.is_spinning:
            sys.stdout.write(f"\r{self.spinner_chars[i % len(self.spinner_chars)]} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    def start(self):
        """Start the spinner animation"""
        if not self.is_spinning:
            self.is_spinning = True
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
    
    def stop(self, final_message: Optional[str] = None):
        """Stop the spinner animation"""
        if self.is_spinning:
            self.is_spinning = False
            if self.thread:
                self.thread.join(timeout=0.2)
            
            # Clear the line and optionally show final message
            sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
            if final_message:
                sys.stdout.write(final_message + "\n")
            sys.stdout.flush()
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


def show_command_execution(command: str):
    """Simple command execution indicator"""
    print(f"⚡ Executing: {command}")


def show_command_result(success: bool, message: str = ""):
    """Show command execution result"""
    if success:
        print(f"✅ {message}" if message else "✅ Command completed")
    else:
        print(f"❌ {message}" if message else "❌ Command failed")