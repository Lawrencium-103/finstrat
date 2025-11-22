        # Fetch 1y of hourly data. yfinance allows up to 730 days for hourly.
        # We'll fetch 1y to be safe and have enough history for indicators.
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y", interval="1h")
        
        if df.empty:
            print(f"No data found for {ticker}")
            return None
            
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def update_database():
    """Iterates through tickers and updates the database."""
    init_db() # Ensure DB exists
    
    for ticker in TICKERS:
        df = fetch_data(ticker)
        if df is not None:
            save_stock_data(df, ticker)
            # Sleep briefly to avoid rate limiting if necessary, though yfinance is usually okay with this volume
            time.sleep(0.5) 
    print("Database update complete.")

if __name__ == "__main__":
    update_database()
