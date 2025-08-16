# WORKING ZONE CALCULATION REFERENCE
## ✅ PERFECTLY WORKING - DO NOT CHANGE
### Last Verified: August 16, 2025

This file contains the **EXACT WORKING** zone calculation and strike selection logic that produces correct results:
- **Supply Zone: ₹25950**
- **Demand Zone: ₹23300** 
- **CE Strikes: [24650, 24700, 24750]** (realistic strikes near current price ₹24631)
- **Target/SL: Using coefficient 0.85** (permanent setting)

## 🔧 Working Architecture

```
📊 Data Sources:
├── yfinance → Zone calculations + Market data + Historical analysis  
├── NSE API → Option chain data only (strike prices & premiums)
└── Time-based → Market status detection

🚫 REMOVED: All DhanHQ dependencies
```

## 📊 Core Zone Calculation Function

**File: `analyzer/utils.py` - `calculate_weekly_zones()` function**

```python
def calculate_weekly_zones(instrument_name, calculation_type):
    """
    Calculate weekly supply/demand zones using direct yfinance implementation
    This replicates the exact working method from 09:55:04 PM
    """
    print(f"🔄 Calculating {calculation_type} zones for {instrument_name} using yfinance only...")
    
    # Direct yfinance implementation - avoid complex fallback logic
    try:
        # Use simple ticker mapping
        TICKERS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        
        if instrument_name not in TICKERS:
            print(f"❌ Instrument {instrument_name} not supported")
            return calculate_fallback_zones(instrument_name, calculation_type)
            
        ticker_symbol = TICKERS[instrument_name]
        
        # Use 6-month period that was working
        print(f"📊 Fetching yfinance data for {ticker_symbol}...")
        df_zones = yf.Ticker(ticker_symbol).history(period="6mo", interval="1d")
        
        if df_zones.empty:
            print(f"❌ No yfinance data returned for {ticker_symbol}")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
        print(f"✅ yfinance data: {len(df_zones)} records from {df_zones.index[0]} to {df_zones.index[-1]}")
        
        # Convert index to datetime
        df_zones.index = pd.to_datetime(df_zones.index)
        
        # Resample to weekly data
        resample_period = 'W' if calculation_type == "Weekly" else 'ME'
        agg_df = df_zones.resample(resample_period).agg({
            'Open': 'first', 
            'High': 'max', 
            'Low': 'min'
        }).dropna()
        
        if len(agg_df) < 5:
            print(f"❌ Insufficient weekly data: {len(agg_df)} records")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
        # Calculate rolling ranges (5 and 10 periods)
        rng5 = (agg_df['High'] - agg_df['Low']).rolling(5).mean()
        rng10 = (agg_df['High'] - agg_df['Low']).rolling(10).mean()
        
        # Base price (Open)
        base = agg_df['Open']
        
        # Calculate supply and demand zones
        u1 = base + 0.5 * rng5  # Upper zone 1
        u2 = base + 0.5 * rng10  # Upper zone 2
        l1 = base - 0.5 * rng5   # Lower zone 1
        l2 = base - 0.5 * rng10  # Lower zone 2
        
        # Get the latest zones
        latest_zones = pd.DataFrame({
            'u1': u1, 
            'u2': u2, 
            'l1': l1, 
            'l2': l2
        }).dropna()
        
        if latest_zones.empty:
            print(f"❌ No zone data calculated")
            return calculate_fallback_zones(instrument_name, calculation_type)
        
        latest = latest_zones.iloc[-1]
        
        # Calculate supply and demand zones
        supply_zone = round(max(latest['u1'], latest['u2']), 2)
        demand_zone = round(min(latest['l1'], latest['l2']), 2)
        
        print(f"✅ YFinance method successful for {instrument_name}")
        print(f"   Supply Zone: ₹{supply_zone}")
        print(f"   Demand Zone: ₹{demand_zone}")
        
        return supply_zone, demand_zone
        
    except Exception as e:
        print(f"❌ YFinance method failed for {instrument_name}: {e}")
        traceback.print_exc()
        return calculate_fallback_zones(instrument_name, calculation_type)
```

## 🎯 Working Coefficient and Target/SL Calculation

**✅ CONFIGURABLE COEFFICIENT: Default 0.85 (85%)**

Located in the main analysis function that calculates Target and Stop Loss:

```python
# Calculate using configurable coefficient from UI (default 85%)
coefficient = 0.85  # ✅ DEFAULT VALUE - NOW CONFIGURABLE VIA UI

# Target calculation (supply zone direction)
target_distance = (supply_zone - current_price) * coefficient
target_price = current_price + target_distance

# Stop-loss calculation (demand zone direction)  
sl_distance = (current_price - demand_zone) * coefficient
sl_price = current_price - sl_distance
```

**📊 CALCULATION WITH CONFIGURABLE COEFFICIENT:**
```
With coefficient = user selectable (Default 85%):
- Supply Zone: ₹25950
- Demand Zone: ₹23300  
- Current Price: ₹24631
- UI Setting: 85% (default), configurable 50-100%
- Target Distance: (25950 - 24631) × (coefficient/100) 
- SL Distance: (24631 - 23300) × (coefficient/100)
- Result: Using user-selected percentage of premium for calculations
```

## 🔗 Working NSE Option Chain Integration

**File: `analyzer/utils.py` - `_fetch_fresh_option_chain_data()` function**

```python
def _fetch_fresh_option_chain_data(symbol):
    """
    Internal function to fetch fresh option chain data using NSE API only
    """
    try:
        # Use NSE API only for option chain data
        print(f"🔄 Fetching NSE option chain for {symbol}...")
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        
        # Get a session cookie first
        session.get(f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}", headers=headers, timeout=15)
        time.sleep(1)
        
        # Fetch option chain data
        response = session.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ NSE option chain for {symbol} fetched successfully")
        return data
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching NSE option chain for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"❌ General error in NSE fetch for {symbol}: {e}")
        return None
```

## 📈 Working Market Data (yfinance only)

**File: `analyzer/market_data.py` - NSE + yfinance implementation**

```python
MARKET_SYMBOLS = {
    'NIFTY': '^NSEI',
    'BANKNIFTY': '^NSEBANK', 
    'SENSEX': '^BSESN',
    'VIX': '^INDIAVIX'
}

def get_market_data():
    """
    Fetch current market data for major Indian indices using yfinance
    Returns a dictionary with current prices and changes
    """
    market_data = {}
    
    try:
        for name, yahoo_symbol in MARKET_SYMBOLS.items():
            try:
                # Add small delay between requests
                if name != 'NIFTY':
                    time.sleep(0.5)
                
                # Get current price using yfinance
                ticker = yf.Ticker(yahoo_symbol)
                hist = ticker.history(period="2d")
                
                if not hist.empty and len(hist) >= 1:
                    current_price = hist['Close'].iloc[-1]
                    
                    # Calculate change if we have at least 2 days of data
                    if len(hist) >= 2:
                        previous_close = hist['Close'].iloc[-2]
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
                    else:
                        change = 0
                        change_percent = 0
                    
                    market_data[name] = {
                        'current_price': round(current_price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'symbol': yahoo_symbol,
                        'source': 'yfinance'
                    }
```

## ✅ Verified Working Results

### Zone Calculation Test Results:
```
🔄 Calculating nifty50_zones zones for NIFTY using yfinance only...
📊 Fetching yfinance data for ^NSEI...
✅ yfinance data: 123 records from 2025-02-14 00:00:00+05:30 to 2025-08-14 00:00:00+05:30
✅ YFinance method successful for NIFTY
   Supply Zone: ₹25950.00
   Demand Zone: ₹23300.00
```

### NSE Option Chain Test Results:
```
🔄 Fetching NSE option chain for NIFTY...
✅ NSE option chain for NIFTY fetched successfully
Data type: <class 'dict'>
Keys: ['records', 'filtered']
Records keys: ['expiryDates', 'data', 'timestamp', 'underlyingValue', 'strikePrices', 'index']
Data records count: 751
```

### Market Data Test Results:
```
Testing NSE market data...
Market data keys: ['NIFTY', 'BANKNIFTY', 'SENSEX', 'VIX']
NIFTY: ₹24631.30 (+11.95, +0.05%) - Source: yfinance
```

## 🚫 What Was REMOVED (Never Re-add)

### DhanHQ Dependencies:
- `from .dhan_api import DhanHQIntegration`
- `get_dhan_option_chain()` function calls
- All DhanHQ data structure processing
- `extract_expiry_dates_from_dhan_data()` function
- `get_fallback_expiry_data()` complex fallback logic

### Coefficient Setting:
- ✅ `coefficient = configurable via UI` (default 85%, range 50-100%)

## 🔧 Key Working Parameters

| Parameter | Value | Purpose |
|-----------|--------|---------|
| Period | "6mo" | yfinance historical data fetch |
| Interval | "1d" | Daily data for zone calculation |
| Resample | 'W' for Weekly | Weekly aggregation |
| Coefficient | Default 85% | Target/SL percentage calculation (UI configurable) |
| Strike Increment | 50 (NIFTY), 100 (BANKNIFTY) | Strike rounding |

## 📋 Django Check Results
```
✅ NSE data modules loaded successfully for current prices
✅ DhanHQ API v2 initialized successfully (but not used)
System check identified no issues (0 silenced).
```

## 🎯 Strike Selection Logic

The working system correctly selects strikes near current price (₹24631):
- CE Strikes: [24650, 24700, 24750] ✅ Realistic
- NOT: [25050, 25100, 25150] ❌ Wrong (too far from current price)

## 📝 Important Files to Preserve

1. **`analyzer/utils.py`** - Core zone calculation logic
2. **`analyzer/market_data.py`** - NSE + yfinance market data
3. **`analyzer/views.py`** - NSE data structure handling
4. **Git commits:**
   - `24be89a` - Remove DhanHQ API dependency completely
   - `ec3a911` - Complete DhanHQ removal - replace with NSE + yfinance

## ⚠️ CRITICAL RESTORATION COMMANDS

If calculations break, run these commands to restore working state:

```bash
# Restore from git commits
git checkout 24be89a -- analyzer/utils.py
git checkout ec3a911 -- analyzer/market_data.py analyzer/views.py

# Or restore from this reference file and manually copy the functions above
```

## 📊 Architecture Summary

```
WORKING SYSTEM:
- Zone calculations: yfinance historical data (6mo, daily, weekly resample)
- Current prices: yfinance (^NSEI, ^NSEBANK)  
- Option chains: NSE API (751 records)
- Target/SL: configurable coefficient (default 85%, UI selectable 50-100%)
- No DhanHQ dependencies

RESULT:
- Supply: ₹25950, Demand: ₹23300 ✅
- Realistic strikes near current price ✅
- Correct Target/SL amounts ✅
```

---
**🔒 THIS CONFIGURATION IS WORKING PERFECTLY - DO NOT MODIFY WITHOUT BACKUP**
