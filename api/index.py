"""Vercel entry point for FastAPI application."""
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app

# Vercel expects 'app' or 'handler' to be exported
handler = app
