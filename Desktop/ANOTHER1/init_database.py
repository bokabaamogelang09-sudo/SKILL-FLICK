#!/usr/bin/env python3
"""
Initialize the database tables for the micro-loans application
"""
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import init_database

if __name__ == "__main__":
    print("Initializing database tables...")
    try:
        init_database()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)