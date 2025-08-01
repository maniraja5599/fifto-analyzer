# analyzer/utils.py - Clean New Implementation

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
import json
import os
import uuid
from datetime import datetime
from django.conf import settings

# Configuration
STATIC_FOLDER_PATH = os.path.join(settings.BASE_DIR, 'static')
SETTINGS_FILE = os.path.join(os.path.expanduser('~'), "app_settings.json")

def load_settings():
    """Load application settings with defaults."""
    defaults = {
        "update_interval": "15 Mins",
        "bot_token": "",
        "chat_id": ""
    }
    
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            loaded = json.load(f)
            defaults.update(loaded)
            return defaults
    except:
        return defaults

def save_settings(settings_data):
    """Save application settings."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def get_option_chain_data(symbol):
    """Fetch option chain data from NSE."""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    try:
        # Get session cookie first
        session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", 
                    headers=headers, timeout=10)
        
        # Fetch option chain
        api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        response = session.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return None

def generate_summary_chart(data, instrument_name, expiry_date):
    """Generate a clean summary chart."""
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('white')
    
    # Title
    title = f"{instrument_name} Options Analysis - {expiry_date}"
    ax.text(0.5, 0.95, title, transform=ax.transAxes, ha='center', 
            fontsize=16, fontweight='bold')
    
    # Create table data
    table_data = []
    for entry in data:
        row = [
            entry['type'],
            f"{entry['ce_strike']:.0f}",
            f"₹{entry['ce_price']:.2f}",
            f"{entry['pe_strike']:.0f}",
            f"₹{entry['pe_price']:.2f}",
            f"₹{entry['premium']:.2f}"
        ]
        table_data.append(row)
    
    # Table headers
    headers = ['Strategy', 'CE Strike', 'CE Price', 'PE Strike', 'PE Price', 'Total Premium']
    
    # Create table
    table = ax.table(cellText=table_data, colLabels=headers,
                     cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2)
    
    # Style the table
    for (row, col), cell in table.get_celld().items():
        if row == 0:  # Header row
            cell.set_facecolor('#4CAF50')
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        else:
            cell.set_facecolor('#f9f9f9')
    
    ax.axis('off')
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ax.text(0.99, 0.01, f"Generated: {timestamp}", transform=ax.transAxes,
            ha='right', va='bottom', fontsize=8, style='italic')
    
    # Save chart
    filename = f"summary_{uuid.uuid4().hex}.png"
    filepath = os.path.join(STATIC_FOLDER_PATH, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return f"static/{filename}"

def generate_payoff_chart(ce_strike, pe_strike, premium, current_price, instrument_name):
    """Generate a payoff diagram."""
    import numpy as np
    
    # Price range for payoff calculation
    price_range = np.linspace(current_price * 0.85, current_price * 1.15, 300)
    
    # Calculate payoff for short straddle/strangle
    payoff = premium - np.maximum(price_range - ce_strike, 0) - np.maximum(pe_strike - price_range, 0)
    
    # Create chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot payoff line
    ax.plot(price_range, payoff, 'b-', linewidth=2, label='Payoff')
    
    # Fill profit/loss areas
    ax.fill_between(price_range, payoff, 0, where=(payoff >= 0), 
                    color='green', alpha=0.3, label='Profit')
    ax.fill_between(price_range, payoff, 0, where=(payoff < 0), 
                    color='red', alpha=0.3, label='Loss')
    
    # Add breakeven lines
    be_lower = pe_strike - premium
    be_upper = ce_strike + premium
    ax.axvline(x=be_lower, color='gray', linestyle='--', alpha=0.7, 
               label=f'Lower BE: {be_lower:.0f}')
    ax.axvline(x=be_upper, color='gray', linestyle='--', alpha=0.7, 
               label=f'Upper BE: {be_upper:.0f}')
    
    # Add current price line
    ax.axvline(x=current_price, color='orange', linestyle='-', alpha=0.8,
               label=f'Current: {current_price:.0f}')
    
    # Zero line
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # Labels and formatting
    ax.set_title(f'{instrument_name} Payoff Diagram', fontsize=14, fontweight='bold')
    ax.set_xlabel('Price at Expiry')
    ax.set_ylabel('Profit/Loss')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Save chart
    filename = f"payoff_{uuid.uuid4().hex}.png"
    filepath = os.path.join(STATIC_FOLDER_PATH, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return f"static/{filename}"

def generate_analysis(instrument_name, calculation_type, selected_expiry_str):
    """Main analysis function - simplified and clean."""
    print(f"Starting analysis for {instrument_name} - {calculation_type} - {selected_expiry_str}")
    
    # Validate inputs
    if not all([instrument_name, calculation_type, selected_expiry_str]):
        return None, "Please provide all required inputs."
    
    # Ticker mapping
    tickers = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    if instrument_name not in tickers:
        return None, "Invalid instrument name."
    
    # Get current price from yfinance
    try:
        ticker = yf.Ticker(tickers[instrument_name])
        hist = ticker.history(period="1d")
        if hist.empty:
            return None, "Could not fetch current price."
        current_price = hist['Close'].iloc[-1]
        print(f"Current price: {current_price}")
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None, f"Error fetching current price: {e}"
    
    # Get option chain data
    option_data = get_option_chain_data(instrument_name)
    if not option_data:
        return None, "Could not fetch option chain data."
    
    # Extract option prices for the selected expiry
    ce_prices = {}
    pe_prices = {}
    
    for item in option_data['records']['data']:
        if item.get('expiryDate') == selected_expiry_str:
            strike = item['strikePrice']
            if item.get('CE'):
                ce_prices[strike] = item['CE']['lastPrice']
            if item.get('PE'):
                pe_prices[strike] = item['PE']['lastPrice']
    
    if not ce_prices or not pe_prices:
        return None, "No option data found for selected expiry."
    
    # Create simple strategies
    strategies = []
    
    # ATM strategy
    atm_strike = min(ce_prices.keys(), key=lambda x: abs(x - current_price))
    if atm_strike in ce_prices and atm_strike in pe_prices:
        strategies.append({
            'type': 'ATM Straddle',
            'ce_strike': atm_strike,
            'pe_strike': atm_strike,
            'ce_price': ce_prices[atm_strike],
            'pe_price': pe_prices[atm_strike],
            'premium': ce_prices[atm_strike] + pe_prices[atm_strike]
        })
    
    # OTM strategy
    otm_ce = min([s for s in ce_prices.keys() if s > current_price], default=atm_strike)
    otm_pe = max([s for s in pe_prices.keys() if s < current_price], default=atm_strike)
    
    if otm_ce in ce_prices and otm_pe in pe_prices:
        strategies.append({
            'type': 'OTM Strangle',
            'ce_strike': otm_ce,
            'pe_strike': otm_pe,
            'ce_price': ce_prices[otm_ce],
            'pe_price': pe_prices[otm_pe],
            'premium': ce_prices[otm_ce] + pe_prices[otm_pe]
        })
    
    if not strategies:
        return None, "Could not create any strategies."
    
    # Generate charts
    try:
        summary_chart = generate_summary_chart(strategies, instrument_name, selected_expiry_str)
        
        # Use first strategy for payoff chart
        main_strategy = strategies[0]
        payoff_chart = generate_payoff_chart(
            main_strategy['ce_strike'],
            main_strategy['pe_strike'], 
            main_strategy['premium'],
            current_price,
            instrument_name
        )
        
        # Prepare result data
        result = {
            'instrument': instrument_name,
            'expiry': selected_expiry_str,
            'current_price': current_price,
            'strategies': strategies,
            'summary_chart': summary_chart,
            'payoff_chart': payoff_chart,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print("Analysis completed successfully!")
        return result, f"Analysis generated successfully for {instrument_name}!"
        
    except Exception as e:
        print(f"Error generating charts: {e}")
        return None, f"Error generating analysis: {e}"
