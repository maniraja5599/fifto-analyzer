import yfinance as yf
from datetime import datetime, timedelta

def simple_zone_test():
    """Simple test for weekly zone calculation"""
    
    instruments = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK"
    }
    
    for name, symbol in instruments.items():
        print(f"\n=== {name} Weekly Zone Test ===")
        
        try:
            # Fetch data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if data.empty:
                print(f"❌ No data available for {name}")
                continue
                
            # Calculate zones
            high = data['High'].max()
            low = data['Low'].min()
            close = data['Close'].iloc[-1]
            open_price = data['Open'].iloc[0]
            
            # Pivot calculation
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high
            
            print(f"✅ Current Price: ₹{close:.2f}")
            print(f"📊 Weekly High: ₹{high:.2f}")
            print(f"📊 Weekly Low: ₹{low:.2f}")
            print(f"📊 Weekly Range: ₹{high - low:.2f}")
            print(f"📊 Pivot Point: ₹{pivot:.2f}")
            print(f"📊 Resistance (R1): ₹{r1:.2f}")
            print(f"📊 Support (S1): ₹{s1:.2f}")
            print(f"📊 Trend: {'Bullish' if close > open_price else 'Bearish'}")
            
            # Strike selection example
            strike_increment = 50 if name == "NIFTY" else 100
            
            # Zone-based strikes
            ce_zone = round(r1 / strike_increment) * strike_increment
            pe_zone = round(s1 / strike_increment) * strike_increment
            
            print(f"🎯 Suggested CE Strike: {ce_zone}")
            print(f"🎯 Suggested PE Strike: {pe_zone}")
            
        except Exception as e:
            print(f"❌ Error for {name}: {e}")

if __name__ == "__main__":
    simple_zone_test()
