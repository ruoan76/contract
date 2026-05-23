"""
Test configuration for backend pytest suite.
Ensure backend is accessible from tests directory.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
