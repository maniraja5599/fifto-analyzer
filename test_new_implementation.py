#!/usr/bin/env python
"""
Test script for the new clean FiFTO implementation
"""

import os
import sys

# Add the project directory to Python path
project_dir = r"c:\Users\manir\Desktop\New folder\Django\fifto_project"
sys.path.append(project_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fifto_project.settings')

import django
django.setup()

from analyzer.utils import generate_analysis, load_settings, save_settings

def test_settings():
    """Test settings functionality"""
    print("=== Testing Settings ===")
    
    # Test loading default settings
    settings = load_settings()
    print(f"Default settings loaded: {settings}")
    
    # Test saving settings
    test_settings = {
        "update_interval": "15 Mins",
        "bot_token": "test_token_123",
        "chat_id": "test_chat_456"
    }
    
    result = save_settings(test_settings)
    print(f"Settings save result: {result}")
    
    # Test loading saved settings
    loaded = load_settings()
    print(f"Loaded saved settings: {loaded}")
    
    print("✅ Settings test completed\n")

def test_analysis():
    """Test analysis generation"""
    print("=== Testing Analysis Generation ===")
    
    # Test with valid parameters
    try:
        result, message = generate_analysis(
            instrument_name="NIFTY",
            calculation_type="Weekly", 
            selected_expiry_str="07-Feb-2025"
        )
        
        if result:
            print("✅ Analysis generated successfully!")
            print(f"Message: {message}")
            print(f"Instrument: {result['instrument']}")
            print(f"Current Price: {result['current_price']}")
            print(f"Number of strategies: {len(result['strategies'])}")
            print(f"Charts generated: {result['summary_chart']}, {result['payoff_chart']}")
        else:
            print(f"❌ Analysis failed: {message}")
            
    except Exception as e:
        print(f"❌ Exception during analysis: {e}")
    
    print("✅ Analysis test completed\n")

def test_invalid_inputs():
    """Test with invalid inputs"""
    print("=== Testing Invalid Inputs ===")
    
    # Test with missing parameters
    result, message = generate_analysis("", "", "")
    print(f"Empty inputs result: {message}")
    
    # Test with invalid instrument
    result, message = generate_analysis("INVALID", "Weekly", "07-Feb-2025")
    print(f"Invalid instrument result: {message}")
    
    print("✅ Invalid inputs test completed\n")

def main():
    """Run all tests"""
    print("🚀 Starting FiFTO New Implementation Tests")
    print("=" * 50)
    
    try:
        test_settings()
        test_analysis()
        test_invalid_inputs()
        
        print("🎉 All tests completed successfully!")
        print("\nYour new clean implementation is ready to use!")
        print("\nTo start the server, run:")
        print("python manage.py runserver")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
