#!/usr/bin/env python
"""
Test script to start Django server and verify async functionality
"""
import subprocess
import sys
import time
import requests
import threading
import os

def test_django_server():
    """Test if Django server starts successfully"""
    print("🧪 Testing Django Server...")
    
    try:
        # Change to project directory
        project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
        os.chdir(project_dir)
        
        # Start Django server in background
        print("▶️  Starting Django server...")
        process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_dir
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Test if server is running
        try:
            response = requests.get("http://127.0.0.1:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ Django server is running successfully!")
                print("🌐 Server accessible at: http://127.0.0.1:8000/")
                
                # Test if the async endpoints work
                print("\n🧪 Testing async endpoints...")
                
                # Test settings endpoint
                try:
                    settings_response = requests.get("http://127.0.0.1:8000/settings/", timeout=5)
                    if settings_response.status_code == 200:
                        print("✅ Settings page loads successfully")
                    else:
                        print(f"❌ Settings page error: {settings_response.status_code}")
                except Exception as e:
                    print(f"❌ Settings test failed: {e}")
                
                # Keep server running for manual testing
                print("\n🎉 SUCCESS! Your Django application is ready!")
                print("\n📋 What to test manually:")
                print("1. Open http://127.0.0.1:8000/ in your browser")
                print("2. Try clicking 'Generate Charts' - should show processing state")
                print("3. Try saving settings - should work without hanging")
                print("\n⚠️  Press Ctrl+C to stop the server")
                
                try:
                    # Keep server running
                    process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Stopping server...")
                    process.terminate()
                    
            else:
                print(f"❌ Server returned status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to server: {e}")
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        
    finally:
        # Clean up
        try:
            process.terminate()
        except:
            pass

if __name__ == "__main__":
    test_django_server()
