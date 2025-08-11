#!/usr/bin/env python3
"""
Quick script to start the Django server
"""
import os
import subprocess
import sys

def start_server():
    """Start the Django development server"""
    try:
        # Change to the project directory
        project_dir = "/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer"
        os.chdir(project_dir)
        
        print("🚀 Starting Django development server...")
        print(f"📁 Project directory: {project_dir}")
        
        # Start the server
        subprocess.run([
            sys.executable, "manage.py", "runserver", "0.0.0.0:8000"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    start_server()
