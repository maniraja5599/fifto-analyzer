#!/usr/bin/env python3
"""
Quick server starter with proper port
"""
import subprocess
import os

def start_server():
    try:
        os.chdir('/Users/maniraja/Desktop/Mani/NIFTY UI/fifto-analyzer')
        print("🚀 Starting Django server on port 8001...")
        subprocess.run(['python3', 'manage.py', 'runserver', '0.0.0.0:8001'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_server()
