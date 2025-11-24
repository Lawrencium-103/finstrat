import pandas as pd
import pandas_ta as ta
from database import load_stock_data

# Define lists explicitly to prevent bleeding
CONSERVATIVE_TICKERS = ["PG", "KO", "PEP", "WMT", "JNJ", "PFE", "XOM", "CVX", "JPM", "BAC"]
MOONSHOT_TICKERS = ["COIN", "PLTR", "DKNG", "ROKU", "SQ", "ARKK", "NVDA", "TSLA", "AMD"]
INDICES = ["SPY", "QQQ", "IWM"]

def calculate_metrics(df):
    """Calculates institutional-grade technical indicators."""
    if df.empty or len(df) < 50:
        # Initialize columns with 0 to prevent KeyErrors
        for col in ['RSI', 'MACD', 'MACD_SIGNAL', 'SMA_20', 'SMA_50', 'SMA_200', 'BBL', 'BBU', 'VOLATILITY', 'VOL_SMA_20', 'ADX', 'ATR', 'RVOL']:
            df[col] = 0
        return df

    # --- Trend ---
    # SMA
    df['SMA_20'] = ta.sma(df['close'], length=20)
    df['SMA_50'] = ta.sma(df['close'], length=50)
    df['SMA_200'] = ta.sma(df['close'], length=200)
    
    # ADX (Trend Strength)
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    if adx is not None and not adx.empty:
        df['ADX'] = adx['ADX_14']
    else:
        df['ADX'] = 0

    # --- Momentum ---
    # RSI
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # MACD
    macd = ta.macd(df['close'])
    if macd is not None:
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
    else:
        df['MACD'] = 0
        df['MACD_SIGNAL'] = 0
    
    # --- Volatility ---
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20)
    if bb is not None and not bb.empty:
        df['BBL'] = bb.get('BBL_20_2.0')
        df['BBU'] = bb.get('BBU_20_2.0')
        # Bandwidth
        if df['BBU'] is not None and df['BBL'] is not None:
            df['VOLATILITY'] = (df['BBU'] - df['BBL']) / df['close']
        else:
            df['VOLATILITY'] = 0
    else:
        df['BBL'] = df['close']
        df['BBU'] = df['close']
        df['VOLATILITY'] = 0
        
    # ATR (Average True Range) for Targets/Stops
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    # --- Volume ---
    # Volume SMA
    df['VOL_SMA_20'] = ta.sma(df['volume'], length=20)
    
    # Relative Volume (RVOL)
    if df['VOL_SMA_20'] is not None:
        df['RVOL'] = df['volume'] / df['VOL_SMA_20']
    else:
        df['RVOL'] = 1.0
    
    # Fill any remaining NaNs
    df.fillna(0, inplace=True)
    
    return df

def score_stock(df, ticker, strategy='balanced'):
    """
    Generates a professional score (0-100) based on multi-factor analysis.
    """
    if df.empty or len(df) < 50:
        return 0, 0, "Insufficient Data"
        
    current = df.iloc[-1]
    score = 0
    reasons = []
    
    # --- 1. Trend Filter (The Foundation) ---
    # A stock must be in a valid trend to even be considered.
    trend_score = 0
    if current['close'] > current['SMA_50']:
        trend_score += 10
        if current['SMA_50'] > current['SMA_200']: # Golden Cross alignment
            trend_score += 10
            
    # ADX Confirmation (Trend Strength)
    if current['ADX'] > 25:
        trend_score += 10
        reasons.append(f"Strong Trend (ADX {current['ADX']:.0f})")
    elif current['ADX'] < 20:
        trend_score -= 5 # Weak trend
        
    # --- 2. Strategy Specifics ---
    
    if strategy == 'conservative':
        # Filter: Must be a stable blue-chip or index
        if ticker not in CONSERVATIVE_TICKERS and ticker not in INDICES:
            return 0, current['close'], "Not a conservative asset"
            
        # Criteria: Pullback in Uptrend
        if trend_score >= 20: # Must be in uptrend
            score += 40
            
            # RSI: Not overbought (Value area)
            if 40 <= current['RSI'] <= 60:
                score += 20
                reasons.append("Fair Value RSI")
            elif current['RSI'] < 40:
                score += 30 # Buy the dip
                reasons.append("Oversold Opportunity")
            elif current['RSI'] > 70:
                score -= 20 # Too expensive
                
            # Low Volatility Preference
            if current.get('VOLATILITY', 0) < 0.03:
                score += 10
            else:
                score -= 10
                
    elif strategy == 'moonshot':
        # Filter: High beta / Growth
        if ticker not in MOONSHOT_TICKERS:
            return 0, current['close'], "Not a growth asset"
            
        # Criteria: High Momentum Breakout
        if trend_score >= 10: # Trend can be emerging
            score += 20
            
        # Relative Volume (Institutional Interest)
        if current.get('RVOL', 1) > 1.5:
            score += 25
            reasons.append(f"High Inst. Volume ({current['RVOL']:.1f}x)")
        elif current.get('RVOL', 1) > 1.2:
            score += 10
            
        # RSI Momentum
        if 55 < current['RSI'] < 75: # Sweet spot for momentum
            score += 25
            reasons.append("Strong Momentum")
        elif current['RSI'] > 80:
            score -= 10 # Blow-off top risk
            
        # MACD Divergence/Cross
        if current['MACD'] > current['MACD_SIGNAL']:
            score += 10
            
    # --- 3. Universal Penalties ---
    if current['close'] < current['SMA_200']:
        score -= 20 # Trading below 200 SMA is dangerous
        
    # Cap score
    score = min(100, max(0, score))
    
    # --- Professional Targets (ATR Based) ---
    atr = current.get('ATR', current['close']*0.02)
    if atr == 0: atr = current['close']*0.02
    
    if strategy == 'moonshot':
        # Target: 3x ATR (Swing trade)
        target_price = current['close'] + (atr * 3)
    else:
        # Target: 1.5x ATR (Conservative swing)
        target_price = current['close'] + (atr * 1.5)
        
    return score, target_price, reasons

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
            
        # Safe access for Volatility
        volatility = df.iloc[-1].get('VOLATILITY', 0)
        
        current_price = df.iloc[-1]['close']
        vol_change = 0
        
        # Safe access for Volume SMA
        if 'VOL_SMA_20' in df.columns and df.iloc[-1]['VOL_SMA_20'] > 0:
            vol_change = (df.iloc[-1]['volume'] - df.iloc[-1]['VOL_SMA_20']) / df.iloc[-1]['VOL_SMA_20']
            
        results.append({
            'Ticker': ticker,
            'Current Price': current_price,
            'Predicted Price': prediction,
            'Upside %': ((prediction - current_price) / current_price) * 100,
            'Confidence Score': score,
            'Signals': ", ".join(reasons),
            'Volatility': volatility,
            'Volume Change': vol_change,
            'ADX': df.iloc[-1].get('ADX', 0),
            'RVOL': df.iloc[-1].get('RVOL', 0)
        })
        
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(by='Confidence Score', ascending=False)
        
    return results_df
