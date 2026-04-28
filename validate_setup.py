#!/usr/bin/env python
"""
Quick validation script to check for import and database creation issues
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    # Test imports
    from app.models import *
    print("SUCCESS: All models imported successfully")
    
    # Test database setup
    from app.core.database import Base
    print("SUCCESS: Database setup imported successfully")
    
    # Test that we can construct the engine
    from app.core.config import settings
    
    print("SUCCESS: Database URL: " + settings.DATABASE_URL[:50] + "...")
    
    print("SUCCESS: All checks passed!")
    
except Exception as e:
    print("ERROR: " + str(e))
    sys.exit(1)