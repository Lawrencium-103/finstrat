import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "stocks.db"

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)

def init_db():
    """Initializes the database with the necessary tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table for storing hourly stock data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker TEXT,
            timestamp DATETIME,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, timestamp)
        )
    ''')
    
    # Table for storing past recommendations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS past_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            strategy TEXT,
            timeframe TEXT,
            entry_price REAL,
            predicted_price REAL,
            confidence_score INTEGER,
            signals TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_pick(pick_data):
    """Saves a single pick to the database."""
    conn = get_connection()
    try:
        # Check if already saved for today/timeframe to avoid duplicates
        # pick_data is a dict
        query = "SELECT id FROM past_picks WHERE date = ? AND ticker = ? AND timeframe = ? AND strategy = ?"
        existing = pd.read_sql(query, conn, params=(pick_data['date'], pick_data['ticker'], pick_data['timeframe'], pick_data['strategy']))
        
        if existing.empty:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO past_picks (date, ticker, strategy, timeframe, entry_price, predicted_price, confidence_score, signals)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pick_data['date'], pick_data['ticker'], pick_data['strategy'], pick_data['timeframe'], 
                  pick_data['entry_price'], pick_data['predicted_price'], pick_data['confidence_score'], pick_data['signals']))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving pick: {e}")
    finally:
        conn.close()
    return False

def get_past_picks():
    """Retrieves all past picks."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM past_picks ORDER BY date DESC", conn)
    conn.close()
    return df

def save_stock_data(df, ticker):
    """Saves stock data to the database."""
    conn = get_connection()
    # Ensure timestamp is the index and convert to string for SQLite compatibility if needed, 
    # but pandas to_sql handles datetime objects well usually.
    # We expect df to have DatetimeIndex.
    
    # We'll reset index to make sure timestamp is a column
    df_reset = df.reset_index()
    
    # Rename columns to match schema if necessary (yfinance usually gives Open, High, Low, Close, Volume)
    df_reset.columns = [c.lower() for c in df_reset.columns]
    
    # Drop extra columns from yfinance that are not in our schema
    cols_to_drop = ['dividends', 'stock splits', 'capital gains']
    for col in cols_to_drop:
        if col in df_reset.columns:
            df_reset.drop(columns=[col], inplace=True)
    
    # Add ticker column
    df_reset['ticker'] = ticker
    
    # We use 'append' and handle duplicates by ignoring them or using a more complex upsert.
    # SQLite doesn't support "ON CONFLICT UPDATE" in standard to_sql.
    # So we'll do a manual check or just use 'append' and let it fail on constraints if we strictly enforced them,
    # but pandas to_sql doesn't support 'INSERT OR IGNORE'.
    # For simplicity in this "no-code friendly" script, we will read existing max date and only append new data.
    
    try:
        # Check for existing data to avoid duplicates
        existing_data = pd.read_sql(f"SELECT MAX(timestamp) as max_date FROM stock_prices WHERE ticker = '{ticker}'", conn)
        last_date = existing_data['max_date'].iloc[0]
        
        if last_date:
            last_date = pd.to_datetime(last_date)
            # Filter df to only include data after last_date
            # Ensure df_reset['datetime'] or 'date' matches the column name from yfinance reset_index
            # yfinance reset_index usually gives 'Date' or 'Datetime'
            
            # Let's standardize column names first
            if 'date' in df_reset.columns:
                df_reset.rename(columns={'date': 'timestamp'}, inplace=True)
            elif 'datetime' in df_reset.columns:
                df_reset.rename(columns={'datetime': 'timestamp'}, inplace=True)
                
            df_to_save = df_reset[df_reset['timestamp'] > last_date]
        else:
            if 'date' in df_reset.columns:
                df_reset.rename(columns={'date': 'timestamp'}, inplace=True)
            elif 'datetime' in df_reset.columns:
                df_reset.rename(columns={'datetime': 'timestamp'}, inplace=True)
            df_to_save = df_reset

        if not df_to_save.empty:
            df_to_save.to_sql('stock_prices', conn, if_exists='append', index=False)
            print(f"Saved {len(df_to_save)} records for {ticker}")
        else:
            print(f"No new data for {ticker}")
            
    except Exception as e:
        print(f"Error saving data for {ticker}: {e}")
    finally:
        conn.close()

def load_stock_data(ticker):
    """Loads stock data from the database."""
    conn = get_connection()
    query = f"SELECT * FROM stock_prices WHERE ticker = '{ticker}' ORDER BY timestamp ASC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    return df

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
