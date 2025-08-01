# analyzer/views.py - Clean New Implementation

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .utils_new import generate_analysis, load_settings, save_settings

def index(request):
    """Main dashboard view."""
    context = {
        'instruments': ['NIFTY', 'BANKNIFTY'],
        'calculation_types': ['Weekly', 'Monthly'],
        'expiry_dates': [
            '07-Feb-2025',
            '14-Feb-2025', 
            '21-Feb-2025',
            '28-Feb-2025',
            '07-Mar-2025',
            '14-Mar-2025'
        ]
    }
    return render(request, 'analyzer/index.html', context)

@require_http_methods(["POST"])
def generate_charts(request):
    """Generate analysis charts."""
    print("=== GENERATE CHARTS VIEW CALLED ===")
    
    try:
        # Get form data
        instrument_name = request.POST.get('instrument_name')
        calculation_type = request.POST.get('calculation_type') 
        selected_expiry = request.POST.get('selected_expiry')
        
        print(f"Form data received:")
        print(f"  Instrument: {instrument_name}")
        print(f"  Calculation Type: {calculation_type}")
        print(f"  Expiry: {selected_expiry}")
        
        # Validate required fields
        if not all([instrument_name, calculation_type, selected_expiry]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('analyzer:index')
        
        # Generate analysis
        print("Calling generate_analysis...")
        analysis_data, message = generate_analysis(
            instrument_name, 
            calculation_type, 
            selected_expiry
        )
        
        if analysis_data is None:
            print(f"Analysis failed: {message}")
            messages.error(request, f"Analysis failed: {message}")
            return redirect('analyzer:index')
        
        print("Analysis successful!")
        messages.success(request, message)
        
        # Store analysis data in session for display
        request.session['analysis_data'] = analysis_data
        
        return redirect('analyzer:index')
        
    except Exception as e:
        print(f"Exception in generate_charts: {e}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('analyzer:index')

def settings_view(request):
    """Settings page view."""
    if request.method == 'POST':
        try:
            # Get form data
            update_interval = request.POST.get('update_interval', '15 Mins')
            bot_token = request.POST.get('bot_token', '').strip()
            chat_id = request.POST.get('chat_id', '').strip()
            
            # Prepare settings data
            settings_data = {
                'update_interval': update_interval,
                'bot_token': bot_token,
                'chat_id': chat_id
            }
            
            # Save settings
            if save_settings(settings_data):
                messages.success(request, "Settings saved successfully!")
            else:
                messages.error(request, "Failed to save settings.")
                
        except Exception as e:
            messages.error(request, f"Error saving settings: {str(e)}")
        
        return redirect('analyzer:settings')
    
    # GET request - show settings form
    current_settings = load_settings()
    context = {
        'settings': current_settings,
        'update_intervals': ['5 Mins', '15 Mins', '30 Mins', '1 Hour']
    }
    return render(request, 'analyzer/settings.html', context)

def trades_view(request):
    """Trades page view."""
    context = {
        'trades': []  # Will implement trade management later
    }
    return render(request, 'analyzer/trades.html', context)
