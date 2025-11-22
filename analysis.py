import pandas as pd
import pandas_ta as ta
from database import load_stock_data

# Define lists explicitly to prevent bleeding
CONSERVATIVE_TICKERS = ["PG", "KO", "PEP", "WMT", "JNJ", "PFE", "XOM", "CVX", "JPM", "BAC"]
MOONSHOT_TICKERS = ["COIN", "PLTR", "DKNG", "ROKU", "SQ", "ARKK", "NVDA", "TSLA", "AMD"]
INDICES = ["SPY", "QQQ", "IWM"]

def calculate_metrics(df):
    """Calculates technical indicators for the given dataframe."""
    if df.empty:
        return df
    
    if len(df) < 50:
        return df

    # RSI
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # MACD
    macd = ta.macd(df['close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
    
    # SMA
    df['SMA_20'] = ta.sma(df['close'], length=20)
    df['SMA_50'] = ta.sma(df['close'], length=50)
    df['SMA_200'] = ta.sma(df['close'], length=200)
    
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20)
    df['BBL'] = bb['BBL_20_2.0']
    df['BBU'] = bb['BBU_20_2.0']
    
    # Volatility (Bandwidth)
    df['VOLATILITY'] = (df['BBU'] - df['BBL']) / df['close']
    
    # Volume SMA
    df['VOL_SMA_20'] = ta.sma(df['volume'], length=20)
    
    return df

def score_stock(df, ticker, strategy='balanced'):
    """
    Generates a score (0-100) based on strategy.
    """
    if df.empty or len(df) < 50:
        return 0, 0, "Insufficient Data"
        
    current = df.iloc[-1]
    score = 0
    reasons = []
    
    # --- Strategy Filters (Strict Ticker Check) ---
    if strategy == 'conservative':
        if ticker not in CONSERVATIVE_TICKERS and ticker not in INDICES:
            return 0, current['close'], "Not a conservative stock"
        
        # Penalize high volatility
        if current['VOLATILITY'] > 0.05: 
            score -= 20
            
    elif strategy == 'moonshot':
        if ticker not in MOONSHOT_TICKERS:
            return 0, current['close'], "Not a moonshot stock"
            
        # Reward high volatility but don't strictly penalize if it's just "okay"
        # We want to see the best of what we have
        if current['VOLATILITY'] > 0.015: # Lowered from 0.02
            score += 15
        
        # Bonus for recent momentum even if not "explosive"
        if current['RSI'] > 50:
            score += 10
            
    # --- Base Logic ---
    
    # 1. Trend (Weighted heavily)
    if current['close'] > current['SMA_50']:
        score += 20
        reasons.append("Bullish Trend")
    
    # 2. Momentum (RSI)
    if strategy == 'moonshot':
        # Explosive momentum
        if current['RSI'] > 55:
            score += 20
            reasons.append("Strong Momentum")
        elif current['RSI'] < 30:
             score += 15
             reasons.append("Oversold Bounce Play")
    else:
        # Steady
        if 40 < current['RSI'] < 70:
            score += 10
            
    # 3. MACD
    if current['MACD'] > current['MACD_SIGNAL']:
        score += 15
        reasons.append("MACD Buy Signal")
        
    # 4. Volume
    if current['volume'] > current['VOL_SMA_20']:
        score += 10
        reasons.append("High Volume")

    # Cap score
    score = min(100, max(0, score))
    
    # Prediction Logic
    volatility = current['VOLATILITY']
    
    # More realistic targets
    if strategy == 'moonshot':
        upside_pct = volatility * 1.5 # 1.5x bandwidth
    else:
        upside_pct = volatility * 0.5 # 0.5x bandwidth
        
    # Timeframe adjustments for target
    if hasattr(df, 'timeframe_mult'): 
        pass
        
    # Restore missing prediction logic
    if score >= 30: # Using the lower cutoff we established
        prediction = current['close'] * (1 + upside_pct)
    else:
        prediction = current['close']
        
    return score, prediction, reasons

def get_top_picks(tickers, timeframe='day', strategy='balanced', min_score=30):
    """Analyzes all tickers and returns top picks for a strategy."""
    results = []
    
    # Filter tickers based on strategy first to save time
    target_tickers = tickers
    if strategy == 'conservative':
        target_tickers = [t for t in tickers if t in CONSERVATIVE_TICKERS or t in INDICES]
    elif strategy == 'moonshot':
        target_tickers = [t for t in tickers if t in MOONSHOT_TICKERS]
    
    for ticker in target_tickers:
        df = load_stock_data(ticker)
        if df.empty:
            continue
            
        # For quarterly, we ideally want longer data, but we'll use what we have (1y hourly)
        # and look for very strong long-term trends.
        
        df = calculate_metrics(df)
        score, prediction, reasons = score_stock(df, ticker, strategy)
        
        # Adjust prediction for timeframe duration
        current_price = df.iloc[-1]['close']
        upside_raw = (prediction - current_price) / current_price
        
        if timeframe == 'week':
            prediction = current_price * (1 + upside_raw * 2) # Expect more move in a week
        elif timeframe == 'month':
            prediction = current_price * (1 + upside_raw * 4)
        elif timeframe == 'quarter':
            prediction = current_price * (1 + upside_raw * 8)
            
        if score < min_score: # Use dynamic cutoff
            continue
            
        current_price = df.iloc[-1]['close']
        vol_change = 0
        if df.iloc[-1]['VOL_SMA_20'] > 0:
            vol_change = (df.iloc[-1]['volume'] - df.iloc[-1]['VOL_SMA_20']) / df.iloc[-1]['VOL_SMA_20']
            
        results.append({
            'Ticker': ticker,
            'Current Price': current_price,
            'Predicted Price': prediction,
            'Upside %': ((prediction - current_price) / current_price) * 100,
            'Confidence Score': score,
            'Signals': ", ".join(reasons),
            'Volatility': df.iloc[-1]['VOLATILITY'],
            'Volume Change': vol_change
        })
        
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(by='Confidence Score', ascending=False)
        
    return results_df
