import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set serverless environment flag
os.environ.setdefault('VERCEL', 'true')

from app import app

# Vercel looks for the WSGI/ASGI 'app' object
app = app
