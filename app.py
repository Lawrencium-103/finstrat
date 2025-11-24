import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from database import load_stock_data as db_load_stock_data, save_pick, get_past_picks, init_db, pick_exists
from analysis import get_top_picks, calculate_metrics, plot_forecast_chart
from data_loader import TICKERS, update_database
from datetime import timedelta, datetime

# Ensure DB is updated with new schema
init_db()

# Caching for performance
@st.cache_data(ttl=900) # Cache for 15 minutes
def load_stock_data(ticker):
    return db_load_stock_data(ticker)

st.set_page_config(page_title="Finstrat", layout="wide", page_icon="📈")

# --- Custom CSS for Modern UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        font-size: 18px; /* Large, readable base size */
        color: #E0E1DD;
        background-color: #0D1B2A; /* Deep Navy Background */
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1B263B;
        border-right: 1px solid #415A77;
    }
    
    /* Sidebar Navigation */
    .stRadio > label {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #8BC34A !important; /* Lime Green for headers */
        padding-bottom: 15px;
    }
    div[role="radiogroup"] > label {
        font-size: 18px !important;
        padding: 12px 10px;
        color: #E0E1DD;
        cursor: pointer;
        transition: color 0.2s;
    }
    div[role="radiogroup"] > label:hover {
        color: #8BC34A; /* Lime Green hover */
    }
    
    /* Glassmorphism Cards */
    .metric-container {
        background: rgba(27, 38, 59, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(139, 195, 74, 0.3); /* Subtle Green Border */
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .metric-label {
        font-size: 16px;
        color: #778DA9;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 36px;
        font-weight: 800;
        color: #FFFFFF;
    }
    
    /* Reduce Top Whitespace */
    /* Reduce Top Whitespace */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        margin-top: -2rem !important;
    }
    
    /* Headers */
    h1 {
        font-family: 'Century Gothic', sans-serif !important;
        font-size: 3.5rem !important; /* Slightly smaller to fit better */
        font-weight: 800 !important;
        background: linear-gradient(90deg, #8BC34A, #FFFFFF); /* Lime to White */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 0.5rem;
        line-height: 1.1;
        margin-bottom: 0.5rem !important;
    }
    h2, h3 {
        font-family: 'Century Gothic', sans-serif !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }
    
    /* Buttons */
    div.stButton > button {
        background: #8BC34A; /* Lime Green */
        color: #0D1B2A; /* Dark Text for Contrast */
        border: none;
        border-radius: 8px;
        padding: 0.8rem 2rem;
        font-size: 18px;
        font-weight: 700;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: #7CB342;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(139, 195, 74, 0.4);
        color: #0D1B2A;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        margin-bottom: 25px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        padding: 0 30px;
        font-size: 18px;
        font-weight: 600;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        color: #E0E1DD;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(139, 195, 74, 0.2);
        border-color: #8BC34A;
        color: #8BC34A;
    }
</style>
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.image("logo.png", width=220)
# st.sidebar.title("Finstrat") # Logo replaces title

# Reordered: Opportunities comes before Past Recommendations
page = st.sidebar.radio("Navigate", ["Overview", "Investment Forecast", "Opportunities", "Past Recommendations", "About Us"])

# Date Context in Sidebar
current_date = datetime.now().strftime("%B %d, %Y")

# Get last data update time
last_update = "Unknown"
try:
    # Use cached loader for metadata too
    spy_df = load_stock_data("SPY")
    if not spy_df.empty:
        last_update = spy_df.index[-1].strftime("%H:%M EST")
except:
    pass

st.sidebar.markdown(f"""
<div style="text-align: center; color: #778DA9; font-size: 0.9rem; margin-top: 10px; margin-bottom: 20px;">
    📅 {current_date}<br>
    <span style="font-size: 0.8rem; color: #415A77;">Data Updated: {last_update}</span>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("Refresh Data", type="primary"):
    with st.spinner("Fetching latest data..."):
        update_database()
    st.success("Data updated!")

# --- Helper Functions ---
def plot_forecast_chart(ticker, df, predicted_price, timeframe='day'):
    """Plots price history with a forecast point."""
    fig = go.Figure()
    
    # Determine forecast delta
    if timeframe == 'week':
        delta = timedelta(days=7)
        label = "1 Week Target"
    elif timeframe == 'month':
        delta = timedelta(days=30)
        label = "1 Month Target"
    elif timeframe == 'quarter':
        delta = timedelta(days=90)
        label = "1 Quarter Target"
    else: # day
        delta = timedelta(hours=24) # Next day
        label = "24h Target"

    # Historical Price
    fig.add_trace(go.Scatter(
        x=df.index, y=df['close'],
        mode='lines', name='Price',
        line=dict(color='#2962FF', width=2),
        hovertemplate='<b>Date</b>: %{x}<br><b>Price</b>: $%{y:.2f}<extra></extra>'
    ))
    
    # Forecast Point
    last_date = df.index[-1]
    next_date = last_date + delta
    
    fig.add_trace(go.Scatter(
        x=[last_date, next_date], 
        y=[df['close'].iloc[-1], predicted_price],
        mode='lines+markers', name='Forecast',
        line=dict(color='#00E676', width=2, dash='dot'),
        marker=dict(size=10, color='#00E676', symbol='star'),
        hovertemplate=f'<b>{label}</b><br>Target: $%{{y:.2f}}<extra></extra>'
    ))
    
    # SMA
    if 'SMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='orange', width=1), name='SMA 50'))

    fig.update_layout(
        title=dict(text=f"{ticker} Price & Forecast ({label})", font=dict(size=18)),
        xaxis_title="Date", yaxis_title="Price",
        height=500,
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def get_news_safe(ticker):
    """Fetches news safely."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        valid_news = []
        for n in news:
            if 'title' in n and 'link' in n:
                # Extract thumbnail if available
                thumb = None
                try:
                    if 'thumbnail' in n and n['thumbnail'] and 'resolutions' in n['thumbnail']:
                        # Get the first resolution (usually adequate)
                        resolutions = n['thumbnail']['resolutions']
                        if resolutions:
                            thumb = resolutions[0]['url']
                except Exception:
                    pass # Ignore thumbnail errors, keep the article
                
                valid_news.append({
                    'title': n['title'],
                    'link': n['link'],
                    'publisher': n.get('publisher', 'Unknown'),
                    'thumbnail': thumb,
                    'time': n.get('providerPublishTime', 0)
                })
        return valid_news
    except:
        return []

# --- Page 1: Overview ---
if page == "Overview":
    # Hero Section
    today = datetime.now().strftime("%B %d, %Y")
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1B263B 0%, #0D1B2A 100%); padding: 40px; border-radius: 16px; border: 1px solid #415A77; margin-bottom: 30px; text-align: center;">
        <h1 style="font-size: 3.5rem; margin-bottom: 10px; background: linear-gradient(90deg, #8BC34A, #FFFFFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Market Overview</h1>
        <p style="font-size: 1.2rem; color: #E0E1DD; max-width: 800px; margin: 0 auto;">
            Real-time tracking of 60+ major US assets | 📅 <b>{today}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_ticker = st.selectbox("Select Ticker", TICKERS)
        compare_tickers = st.multiselect("Compare with", [t for t in TICKERS if t != selected_ticker])
    
    df = load_stock_data(selected_ticker)
    if not df.empty:
        df = calculate_metrics(df)
        
        current_price = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        daily_change = ((current_price - prev_close) / prev_close) * 100
        
        # Metrics Row
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Price", f"${current_price:.2f}", f"{daily_change:.2f}%")
        
        vol_change = 0
        if df['VOL_SMA_20'].iloc[-1] > 0:
            vol_change = ((df['volume'].iloc[-1] - df['VOL_SMA_20'].iloc[-1]) / df['VOL_SMA_20'].iloc[-1]) * 100
        m2.metric("Volume vs Avg", f"{df['volume'].iloc[-1]:,}", f"{vol_change:.1f}%", delta_color="off")
        
        rsi = df['RSI'].iloc[-1]
        m3.metric("RSI (14)", f"{rsi:.1f}", "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral", delta_color="off")
        
        # Charts
        st.plotly_chart(plot_forecast_chart(selected_ticker, df, current_price), use_container_width=True)
        
        # Comparison Chart
        if compare_tickers:
            st.subheader("Relative Performance Comparison")
            comp_fig = go.Figure()
            
            # Base Ticker
            base_start = df['close'].iloc[0]
            if base_start > 0:
                comp_fig.add_trace(go.Scatter(
                    x=df.index, 
                    y=(df['close'] / base_start - 1) * 100, 
                    name=selected_ticker,
                    hovertemplate='%{y:.2f}%'
                ))
            
            for t in compare_tickers:
                cdf = load_stock_data(t)
                if not cdf.empty:
                    c_start = cdf['close'].iloc[0]
                    if c_start > 0:
                        comp_fig.add_trace(go.Scatter(
                            x=cdf.index, 
                            y=(cdf['close'] / c_start - 1) * 100, 
                            name=t,
                            hovertemplate='%{y:.2f}%'
                        ))
            
            comp_fig.update_layout(
                xaxis_title="Date", yaxis_title="% Change",
                template="plotly_dark", hovermode="x unified"
            )
            st.plotly_chart(comp_fig, use_container_width=True)

# --- Page 2: Forecast ---
elif page == "Investment Forecast":
    st.markdown("# 🚀 Algorithmic Investment Forecast")
    
    # Strategy Toggle
    strategy_tab = st.radio("Select Strategy", ["Conservative (Safe)", "Moonshot (High Risk)"], horizontal=True)
    strategy_code = 'conservative' if "Conservative" in strategy_tab else 'moonshot'
    
    st.markdown("---")
    
    t1, t2, t3, t4 = st.tabs(["Daily Picks", "Weekly Picks", "Monthly Picks", "Quarterly Picks"])
    
    def display_picks(timeframe):
        # Try to get picks with standard threshold
        picks = get_top_picks(TICKERS, timeframe=timeframe, strategy=strategy_code, min_score=30)
        is_fallback = False
        
        # Fallback: If empty, get "Potential" picks (score > 0)
        if picks.empty:
            picks = get_top_picks(TICKERS, timeframe=timeframe, strategy=strategy_code, min_score=0)
            is_fallback = True
        
        if not picks.empty:
            best = picks.iloc[0]
            
            if is_fallback:
                st.warning(f"No strong signals found for {strategy_tab}. Showing top potential candidates based on volatility.")
            
            # Hero Section
            pick_date = datetime.now().strftime("%b %d, %H:%M")
            st.markdown(f"""
            <div style="background-color: #004D40; padding: 20px; border-radius: 10px; border: 1px solid #00695C; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin:0; color: #E0F2F1;">🏆 Top Pick: {best['Ticker']}</h2>
                    <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; color: #B2DFDB;">📅 {pick_date}</span>
                </div>
                <h3 style="margin-top:10px; color: #69F0AE;">Target: ${best['Predicted Price']:.2f} (+{best['Upside %']:.2f}%)</h3>
                <p style="margin-top:5px; color: #B2DFDB;">{best['Signals']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Detailed Metrics for Top Pick
            best_df = load_stock_data(best['Ticker'])
            if not best_df.empty:
                best_df = calculate_metrics(best_df)
                
                # Metrics Grid
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f"<div class='metric-container'><div class='metric-label'>RSI</div><div class='metric-value'>{best_df['RSI'].iloc[-1]:.1f}</div></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='metric-container'><div class='metric-label'>MACD</div><div class='metric-value'>{best_df['MACD'].iloc[-1]:.3f}</div></div>", unsafe_allow_html=True)
                with c3:
                    vol = best['Volatility']
                    st.markdown(f"<div class='metric-container'><div class='metric-label'>Volatility</div><div class='metric-value'>{vol:.2%}</div></div>", unsafe_allow_html=True)
                with c4:
                    vc = best['Volume Change']
                    color = "#00E676" if vc > 0 else "#FF5252"
                    st.markdown(f"<div class='metric-container'><div class='metric-label'>Vol Change</div><div class='metric-value' style='color:{color}'>{vc:.1%}</div></div>", unsafe_allow_html=True)
                
                st.write("") # Spacer
                
                # Chart
                st.plotly_chart(plot_forecast_chart(best['Ticker'], best_df, best['Predicted Price'], timeframe), use_container_width=True)
            
            # Auto-Save Top Pick
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # Check if we already have a pick for this day/strategy/timeframe
            if not pick_exists(today_str, best['Ticker'], strategy_code, timeframe):
                pick_data = {
                    'date': today_str,
                    'ticker': best['Ticker'],
                    'strategy': strategy_code,
                    'timeframe': timeframe,
                    'entry_price': best['Current Price'],
                    'predicted_price': best['Predicted Price'],
                    'confidence_score': best['Confidence Score'],
                    'signals': best['Signals']
                }
                save_pick(pick_data)
                # No toast needed to avoid spam, it just happens silently

            # Table
            st.subheader("All Candidates")
            st.dataframe(picks.style.format({
                'Current Price': '${:.2f}',
                'Predicted Price': '${:.2f}',
                'Upside %': '{:.2f}%',
                'Confidence Score': '{:.0f}',
                'Volatility': '{:.2%}',
                'Volume Change': '{:.1%}'
            }), use_container_width=True)
            
            # News
            st.markdown(f"### 📰 Latest News for {best['Ticker']}")
            news = get_news_safe(best['Ticker'])
            if news:
                for n in news[:5]: # Show top 5
                    with st.container():
                        nc1, nc2 = st.columns([1, 4])
                        with nc1:
                            if n['thumbnail']:
                                st.image(n['thumbnail'], use_container_width=True)
                            else:
                                st.markdown("📰")
                        with nc2:
                            st.markdown(f"**[{n['title']}]({n['link']})**")
                            st.caption(f"Source: {n['publisher']}")
                        st.markdown("---")
            else:
                st.info("No recent news found.")
        else:
            st.error(f"No data available for {strategy_tab}. Please check your internet connection or data source.")

    with t1:
        st.info("Strategy: Buy Today, Sell Tomorrow.")
        display_picks('day')
    with t2:
        st.info("Strategy: Buy Monday, Sell Friday.")
        display_picks('week')
    with t3:
        st.info("Strategy: Buy 1st of Month, Sell End of Month.")
        display_picks('month')
    with t4:
        st.info("Strategy: Quarterly Hold.")
        display_picks('quarter')

# --- Page 3: Past Recommendations ---
elif page == "Past Recommendations":
    st.markdown("# 📜 Past Recommended Stocks")
    st.markdown("Historical record of AI-generated top picks. These are automatically saved when generated.")
    
    history_df = get_past_picks()
    
    if not history_df.empty:
        # Create tabs for each timeframe
        ht1, ht2, ht3, ht4 = st.tabs(["Daily History", "Weekly History", "Monthly History", "Quarterly History"])
        
        def show_history_table(timeframe_filter):
            filtered_df = history_df[history_df['timeframe'] == timeframe_filter].copy()
            if not filtered_df.empty:
                # Format for display
                display_df = filtered_df[['date', 'ticker', 'strategy', 'entry_price', 'predicted_price', 'signals']].copy()
                display_df.columns = ['Date', 'Ticker', 'Strategy', 'Entry Price', 'Target Price', 'Signals']
                
                # Ensure numeric columns are floats to prevent TypeError
                display_df['Entry Price'] = pd.to_numeric(display_df['Entry Price'], errors='coerce').fillna(0)
                display_df['Target Price'] = pd.to_numeric(display_df['Target Price'], errors='coerce').fillna(0)
                
                st.dataframe(display_df.style.format({
                    'Entry Price': '${:.2f}',
                    'Target Price': '${:.2f}'
                }), use_container_width=True)
            else:
                st.info(f"No history yet for {timeframe_filter} picks.")

        with ht1:
            show_history_table('day')
        with ht2:
            show_history_table('week')
        with ht3:
            show_history_table('month')
        with ht4:
            show_history_table('quarter')
            
    else:
        st.info("No past recommendations found yet. Visit the Investment Forecast page to generate and auto-save picks.")
            
# --- Page 4: Opportunities ---
elif page == "Opportunities":
    st.markdown("# 💰 Investment Opportunities")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏛️ Fixed Income / Bonds")
        st.info("When yields are high, bonds are a safe alternative to stocks.")
        st.metric("10-Year Treasury Yield", "4.25%", "-0.05%")
        st.metric("2-Year Treasury Yield", "4.50%", "+0.02%")
        
    with col2:
        st.markdown("### 📅 Economic Calendar")
        st.markdown("""
        | Date | Event | Impact |
        | :--- | :--- | :--- |
        | **Nov 14** | CPI Release | 🔴 High |
        | **Dec 08** | Non-Farm Payrolls | 🔴 High |
        | **Dec 13** | FOMC Meeting | 🔴 High |
        """)

# --- Page 5: About Us ---
elif page == "About Us":
    st.markdown("# ℹ️ About Us")
    
    st.markdown("""
    ### The Dashboard
    
    This **Autonomous Finance Dashboard** bridges the gap between raw market data and actionable investment insights. It uses **automated data pipelines** and **algorithmic technical analysis** to identify high-probability opportunities in real-time.
    
    **Core Capabilities:**
    *   **Autonomous Tracking**: Monitors 24/7 market movements across 60+ major US stocks.
    *   **Algorithmic Forecasting**: Predicts price targets for Daily, Weekly, and Quarterly timeframes.
    *   **Dual-Strategy Engine**: Filters opportunities for **Conservative** (steady growth) and **Moonshot** (high volatility) profiles.
    
    **Target Audience:**
    *   **Investors** seeking data-backed validation.
    *   **Traders** looking for automated screening.
    *   **Businesses** demonstrating advanced data engineering capabilities.
    
    > ⚠️ **Disclaimer**: *This application is for informational and educational purposes only. It does not constitute financial advice. Always conduct your own due diligence.*
    
    ---
    """)
    
    st.markdown("### 👨‍💻 Meet the Creator")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image("https://api.dicebear.com/7.x/avataaars/svg?seed=Alexander", width=200)
        st.markdown("""
        **Lawrence Oladeji**  
        *Data Associate, Dashboard Developer & Workflow Automation Developer*  
        📧 [oladeji.lawrence@gmail.com](mailto:oladeji.lawrence@gmail.com)
        """)
        
    with col2:
        st.markdown("""
        **"I build systems that turn complex data into clear, profitable decisions."**
        
        I specialize in creating end-to-end data solutions—from robust backend engineering to user-centric frontends. My work spans the **Energy, Health, Finance, NGO, and Supply Chain** sectors.
        
        #### 🛠️ The Power Stack
        *   **Core Engineering**: Python, R, SQL, STATA
        *   **Big Data & Cloud**: Microsoft Fabric, Azure Databricks, AWS (EC2, S3), Google Cloud
        *   **Advanced Capabilities**: Web Scraping, RAG Chatbots, AI Agents, Simulation Modeling, Automation Workflows (n8n)
        *   **Visualization**: Streamlit, Tableau, PowerBI
        
        **Looking to build a similar solution?**  
        I am available for consulting and development projects. Let's transform your data strategy.
        """)
