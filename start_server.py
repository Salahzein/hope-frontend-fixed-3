#!/usr/bin/env python3
import uvicorn
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Reddit Lead Finder MVP server...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)

