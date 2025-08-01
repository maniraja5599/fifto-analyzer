#!/usr/bin/env python
"""
Test script to start Django server with debug output
"""
import os
import sys
import subprocess

def main():
    print("🧪 Testing Django FiFTO Application")
    print("=====================================")
    
    # Change to project directory
    project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
    print(f"Project directory: {project_dir}")
    
    try:
        os.chdir(project_dir)
        print("✅ Changed to project directory")
    except Exception as e:
        print(f"❌ Error changing directory: {e}")
        return
    
    print("\n🚀 Starting Django development server...")
    print("📝 Watch the terminal for debug output when you click 'Generate Chart'")
    print("🌐 Open browser to: http://127.0.0.1:8000/")
    print("⚠️  Press Ctrl+C to stop the server")
    print("=====================================\n")
    
    # Start Django server
    try:
        subprocess.run([sys.executable, "manage.py", "runserver", "8000"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
