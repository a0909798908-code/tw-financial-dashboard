import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import logging
from datetime import datetime

import os

# Setup configuration
BACKEND_URL = "https://tw-financial-dashboard.onrender.com"

st.set_page_config(
    page_title="智慧財經資訊儀表板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CSS injection for high-end aesthetics
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', 'Noto Sans TC', sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Title Gradient */
    .title-gradient {
        background: linear-gradient(90deg, #58a6ff 0%, #1f6feb 50%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    .subtitle-gradient {
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Glassmorphism Cards */
    .dashboard-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 65, 0.6);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.2rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .dashboard-card:hover {
        transform: translateY(-3px);
        border-color: #388bfd;
        box-shadow: 0 12px 30px rgba(56, 139, 253, 0.15);
    }
    
    /* Up and Down color indicators (Taiwan standard: Up is Red, Down is Green) */
    .stock-up {
        color: #ff7b72 !important;
        font-weight: bold;
    }
    .stock-down {
        color: #56d364 !important;
        font-weight: bold;
    }
    .stock-neutral {
        color: #8b949e !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #090c10 !important;
        border-right: 1px solid #30363d;
    }
    
    /* Custom KPI metrics wrapper */
    .kpi-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        flex-wrap: wrap;
    }
    .kpi-card {
        flex: 1;
        min-width: 200px;
        background: rgba(22, 27, 34, 0.5);
        border-left: 4px solid #1f6feb;
        border-radius: 6px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    /* Custom news item styling */
    .news-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.2s;
    }
    .news-card:hover {
        background: #1c2128;
        border-color: #58a6ff;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-weight: 600;
        font-size: 16px;
        background-color: transparent;
        border-bottom: 2px solid transparent;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom-color: #58a6ff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper API functions
def api_get(endpoint: str, params: dict = None):
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=12)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error {endpoint}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"API Connection error for {endpoint}: {e}")
        return None

def api_post(endpoint: str, json_data: dict = None):
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error {endpoint}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"API Connection error for {endpoint}: {e}")
        return None

def api_delete(endpoint: str):
    try:
        response = requests.delete(f"{BACKEND_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error {endpoint}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"API Connection error for {endpoint}: {e}")
        return None

# Inject custom styles
inject_custom_css()

# Sidebar Navigation
st.sidebar.markdown("<div style='text-align: center; padding: 10px;'><h2 style='color: #58a6ff;'>🚀 AI Smart Fin</h2><p style='color: #8b949e; font-size: 0.85rem;'>台灣股市&ETF分析儀表板</p></div>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu_options = [
    "🏠 首頁儀表板",
    "🔍 股票資料查詢",
    "📊 ETF 資訊查詢",
    "📈 技術指標分析",
    "📰 財經新聞 & AI 摘要",
    "⭐ 個人關注清單"
]
choice = st.sidebar.radio("請選擇頁面", menu_options)

# Show Sync Status / Trigger button at the bottom of the sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("系統管理")
if st.sidebar.button("🔄 同步台股上市櫃清單"):
    with st.spinner("同步中..."):
        res = api_get("/api/sync")
        if res and res.get("status") == "success":
            st.sidebar.success("同步完成！")
        else:
            st.sidebar.error("同步失敗。")

st.sidebar.info("資料來源：Yahoo Finance, TWSE\nAI 模型：OpenAI GPT-4o-mini")

# Helper component: Search Auto-complete selectbox
def security_search_box(key="search"):
    query = st.text_input("輸入股票/ETF代碼或中文名稱（例如: 2330, 台積電, 0050）", key=f"ti_{key}")
    if query:
        search_results = api_get("/api/search", params={"q": query})
        if search_results and search_results.get("results"):
            options = search_results["results"]
            # Format display label: "2330 - 台積電 [上市]"
            display_options = [f"{o['code']} - {o['name']} [{o['market_type']}]" for o in options]
            selected = st.selectbox("請選擇具體證券", display_options, key=f"sb_{key}")
            if selected:
                # Return selected code
                return selected.split(" - ")[0]
        else:
            st.warning("查無此證券，請檢查輸入或點擊左下角同步上市櫃清單。")
    return None

# ==========================================
# PAGE 1: 首頁儀表板
# ==========================================
if choice == "🏠 首頁儀表板":
    st.markdown("<h1 class='title-gradient'>🏠 首頁儀表板</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>即時大盤走勢、熱門股與最新財經動態</p>", unsafe_allow_html=True)
    
    # Check Backend connection
    status = api_get("/")
    if not status:
        st.error("⚠️ 無法連線至後端 FastAPI 伺服器，請確保 FastAPI 已啟動於 `http://127.0.0.1:8000`。")
        st.stop()
        
    # Col 1: 大盤 & 熱門股, Col 2: 新聞摘要
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("📈 大盤走勢 (加權指數 ^TWII)")
        # Fetch TAIEX Index
        taiex_quote = api_get("/api/stock/^TWII")
        if taiex_quote:
            price = taiex_quote["price"]
            change = taiex_quote["change"]
            change_percent = taiex_quote["change_percent"]
            
            # Format indicators
            color_class = "stock-up" if change >= 0 else "stock-down"
            sign = "+" if change >= 0 else ""
            
            st.markdown(f"""
            <div class='dashboard-card'>
                <h3 style='margin: 0;'>台灣加權股價指數</h3>
                <h1 style='margin: 10px 0 0 0; font-size: 2.5rem;'>{price:,.2f}</h1>
                <p style='margin: 5px 0 0 0; font-size: 1.2rem;' class='{color_class}'>
                    {sign}{change:,.2f} ({sign}{change_percent:.2f}%)
                </p>
                <span style='color: #8b949e; font-size: 0.8rem;'>更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (延遲15分鐘)</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Draw brief TAIEX line chart
            history_res = api_get("/api/stock/^TWII/history", params={"period": "1mo"})
            if history_res and "history" in history_res:
                hist_df = pd.DataFrame(history_res["history"])
                if not hist_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_df['Date'],
                        y=hist_df['Close'],
                        mode='lines',
                        name='收盤價',
                        line=dict(color='#58a6ff', width=2.5),
                        fill='tozeroy',
                        fillcolor='rgba(88, 166, 255, 0.1)'
                    ))
                    fig.update_layout(
                        title="加權指數 近一個月走勢圖",
                        template="plotly_dark",
                        height=250,
                        margin=dict(l=30, r=30, t=40, b=20),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)', side='right')
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暫時無法取得大盤加權指數資訊 (^TWII)。")
            
        # Hot Securities Section
        st.subheader("🔥 熱門關注證券")
        hot_codes = ["2330", "0050", "2317", "0056"]
        hot_cols = st.columns(len(hot_codes))
        
        for idx, code in enumerate(hot_codes):
            with hot_cols[idx]:
                quote = api_get(f"/api/stock/{code}")
                if quote:
                    color_class = "stock-up" if quote["change"] >= 0 else "stock-down"
                    sign = "+" if quote["change"] >= 0 else ""
                    st.markdown(f"""
                    <div class='dashboard-card' style='padding: 1rem; text-align: center;'>
                        <strong style='font-size: 1.1rem; color: #58a6ff;'>{quote['name']}</strong>
                        <div style='color: #8b949e; font-size: 0.8rem;'>{code}</div>
                        <h2 style='margin: 8px 0;'>{quote['price']:.2f}</h2>
                        <span class='{color_class}' style='font-size: 0.9rem;'>{sign}{quote['change_percent']:.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.write(f"無 {code} 資料")
                    
    with col2:
        st.subheader("📰 即時財經新聞")
        news_res = api_get("/api/news")
        if news_res and news_res.get("news"):
            # Show top 4 news items
            for news in news_res["news"][:4]:
                st.markdown(f"""
                <div class='news-card'>
                    <h4 style='margin: 0 0 8px 0;'><a href='{news['link']}' target='_blank' style='text-decoration: none; color: #58a6ff;'>{news['title']}</a></h4>
                    <p style='color: #8b949e; font-size: 0.85rem; margin: 0 0 10px 0;'>時間：{news['pub_date']}</p>
                    <p style='font-size: 0.9rem; line-height: 1.4; color: #c9d1d9; margin: 0;'>{news['summary']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暫無即時新聞。")

# ==========================================
# PAGE 2: 股票資料查詢
# ==========================================
elif choice == "🔍 股票資料查詢":
    st.markdown("<h1 class='title-gradient'>🔍 股票資料查詢</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>查詢台灣上市櫃股票即時報價、歷史走勢與財務基本指標</p>", unsafe_allow_html=True)
    
    code = security_search_box(key="stock_query")
    
    if code:
        # Fetch Realtime Quote
        quote = api_get(f"/api/stock/{code}")
        if quote:
            # Check watchlist status
            watchlist = api_get("/api/watchlist")
            is_watchlisted = False
            if watchlist and watchlist.get("watchlist"):
                is_watchlisted = any(item["code"] == code for item in watchlist["watchlist"])
                
            # Header line: Name, Code and Watchlist Button
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"## {quote['name']} ({quote['code']}) <span style='font-size: 1.2rem; color: #8b949e;'>{quote['industry_type']} | {quote['market_type']}</span>", unsafe_allow_html=True)
            with c2:
                if is_watchlisted:
                    if st.button("⭐ 移出關注清單", use_container_width=True):
                        if api_delete(f"/api/watchlist/remove/{code}"):
                            st.success("已移出關注清單")
                            st.rerun()
                else:
                    if st.button("➕ 加入關注清單", use_container_width=True):
                        if api_post("/api/watchlist/add", json_data={"code": code}):
                            st.success("已加入關注清單")
                            st.rerun()
                            
            # Highlight Cards
            change_color = "stock-up" if quote["change"] >= 0 else "stock-down"
            sign = "+" if quote["change"] >= 0 else ""
            
            st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>最新股價</div>
                    <div style='font-size: 1.8rem; font-weight: bold; margin-top: 5px;'>{quote['price']:.2f}</div>
                    <div style='font-size: 0.9rem;' class='{change_color}'>{sign}{quote['change']:.2f} ({sign}{quote['change_percent']:.2f}%)</div>
                </div>
                <div class='kpi-card' style='border-left-color: #56d364;'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>今日開盤 / 高 / 低</div>
                    <div style='font-size: 1.4rem; font-weight: bold; margin-top: 8px;'>{quote['open']:.2f} / {quote['high']:.2f} / {quote['low']:.2f}</div>
                </div>
                <div class='kpi-card' style='border-left-color: #e3b341;'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>當日成交量</div>
                    <div style='font-size: 1.6rem; font-weight: bold; margin-top: 5px;'>{quote['volume']:,} 股</div>
                </div>
                <div class='kpi-card' style='border-left-color: #bc8cff;'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>本益比 / 殖利率</div>
                    <div style='font-size: 1.5rem; font-weight: bold; margin-top: 5px;'>
                        {"N/A" if quote['pe_ratio'] is None else f"{quote['pe_ratio']:.2f}"} / 
                        {"N/A" if quote['dividend_yield'] is None else f"{quote['dividend_yield']*100:.2f}%"}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            # Sub-Tab structure: Historical Chart, AI Analytical Report
            tab1, tab2 = st.tabs(["📊 歷史 K 線走勢圖", "🤖 AI 投資報告分析"])
            
            with tab1:
                period_choice = st.selectbox("選擇歷史區間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
                history_data = api_get(f"/api/stock/{code}/history", params={"period": period_choice})
                if history_data and history_data.get("history"):
                    hist_df = pd.DataFrame(history_data["history"])
                    
                    # Draw Plotly Candlestick Chart
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=hist_df['Date'],
                        open=hist_df['Open'],
                        high=hist_df['High'],
                        low=hist_df['Low'],
                        close=hist_df['Close'],
                        name='K線',
                        increasing_line_color='#ff7b72', increasing_fillcolor='#ff7b72',  # Red up for TW
                        decreasing_line_color='#56d364', decreasing_fillcolor='#56d364'   # Green down for TW
                    ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{quote['name']} K線歷史走勢圖 ({period_choice})",
                        template="plotly_dark",
                        xaxis_rangeslider_visible=False,
                        height=500,
                        yaxis_title="股價 (TWD)",
                        margin=dict(l=50, r=50, t=50, b=50)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("查無歷史股價資料。")
                    
            with tab2:
                st.subheader("🤖 AI 智慧投資報告")
                st.markdown("點擊下方按鈕，AI 將為您即時整合財報與近期走勢，生成該股之多空因素與風險分析報告。")
                if st.button("🚀 生成 AI 投資報告", key="gen_report_btn"):
                    with st.spinner("AI 正在分析數據中，請稍候..."):
                        report_res = api_post(f"/api/ai/report/{code}")
                        if report_res and report_res.get("report"):
                            st.markdown("---")
                            st.markdown(report_res["report"])
                            st.markdown("---")
                        else:
                            st.error("AI 報告生成失敗，請確認 OpenAI API 設定是否正確。")

# ==========================================
# PAGE 3: ETF 資訊查詢
# ==========================================
elif choice == "📊 ETF 資訊查詢":
    st.markdown("<h1 class='title-gradient'>📊 ETF 資訊查詢</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>查詢 ETF 的績效表現、配息歷史與前十大成份股權重</p>", unsafe_allow_html=True)
    
    code = security_search_box(key="etf_query")
    
    if code:
        etf_details = api_get(f"/api/etf/{code}")
        if etf_details:
            quote = etf_details["quote"]
            div_yield = etf_details["dividend_yield"]
            div_history = etf_details["dividend_history"]
            holdings = etf_details["holdings"]
            
            # Header info
            st.markdown(f"## {quote['name']} ({quote['code']}) <span style='font-size: 1.2rem; color: #8b949e;'>{etf_details['category']} | {quote['market_type']}</span>", unsafe_allow_html=True)
            
            # Highlights
            change_color = "stock-up" if quote["change"] >= 0 else "stock-down"
            sign = "+" if quote["change"] >= 0 else ""
            st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>最新價格</div>
                    <div style='font-size: 1.8rem; font-weight: bold; margin-top: 5px;'>{quote['price']:.2f}</div>
                    <div style='font-size: 0.9rem;' class='{change_color}'>{sign}{quote['change']:.2f} ({sign}{quote['change_percent']:.2f}%)</div>
                </div>
                <div class='kpi-card' style='border-left-color: #e3b341;'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>配息率 (年化估算)</div>
                    <div style='font-size: 1.8rem; font-weight: bold; margin-top: 5px; color: #e3b341;'>{div_yield:.2f}%</div>
                </div>
                <div class='kpi-card' style='border-left-color: #bc8cff;'>
                    <div style='color: #8b949e; font-size: 0.85rem;'>基金發行公司</div>
                    <div style='font-size: 1.5rem; font-weight: bold; margin-top: 8px;'>{etf_details['category']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            # Layout cols: holdings table on left, dividend bar chart on right
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("💼 前十大成分股")
                if holdings:
                    holdings_df = pd.DataFrame(holdings)
                    # format symbol and percent
                    holdings_df.columns = ["證券代碼", "中文名稱", "權重 (%)"]
                    st.dataframe(holdings_df, use_container_width=True, hide_index=True)
                else:
                    st.info("無該 ETF 成分股資訊")
                    
            with c2:
                st.subheader("💵 歷史配息記錄")
                if div_history:
                    div_df = pd.DataFrame(div_history)
                    div_df = div_df.sort_values(by="date")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=div_df['date'],
                        y=div_df['amount'],
                        marker_color='#e3b341',
                        name='配息金額 (元)'
                    ))
                    fig.update_layout(
                        template="plotly_dark",
                        xaxis_title="配息基準日",
                        yaxis_title="配息金額 (TWD)",
                        height=350,
                        margin=dict(l=30, r=20, t=20, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("該 ETF 無配息歷史資料")
        else:
            st.error("此證券似乎不是 ETF 或無法讀取 ETF 資訊。請在股票查詢頁面搜尋。")

# ==========================================
# PAGE 4: 技術指標分析
# ==========================================
elif choice == "📈 技術指標分析":
    st.markdown("<h1 class='title-gradient'>📈 技術指標分析</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>繪製包含移動平均線 (MA)、相對強弱指標 (RSI) 及平滑異同移動平均線 (MACD) 的整合性互動圖表</p>", unsafe_allow_html=True)
    
    code = security_search_box(key="tech_query")
    
    if code:
        period_choice = st.selectbox("選擇歷史區間", ["3mo", "6mo", "1y", "2y"], index=1)
        
        with st.spinner("計算指標中..."):
            tech_data = api_get(f"/api/stock/{code}/technical", params={"period": period_choice})
            
        if tech_data and tech_data.get("indicators"):
            df = pd.DataFrame(tech_data["indicators"])
            quote = api_get(f"/api/stock/{code}")
            
            st.subheader(f"📊 {quote['name']} ({code}) 技術指標全圖")
            
            # Setup Plotly Subplots
            # Row 1: Candlestick + MAs (height 3)
            # Row 2: MACD (height 1)
            # Row 3: RSI (height 1)
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[0.5, 0.25, 0.25]
            )
            
            # 1. Candlestick on Row 1
            fig.add_trace(go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='K線',
                increasing_line_color='#ff7b72', increasing_fillcolor='#ff7b72',
                decreasing_line_color='#56d364', decreasing_fillcolor='#56d364',
                showlegend=True
            ), row=1, col=1)
            
            # Add MAs to Row 1
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MA5'], line=dict(color='#ffd60a', width=1.2), name='MA5'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='#ff6b6b', width=1.5), name='MA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], line=dict(color='#4d96ff', width=1.8), name='MA60'), row=1, col=1)
            
            # 2. MACD on Row 2
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], line=dict(color='#8b949e', width=1.5), name='MACD'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD_Signal'], line=dict(color='#ff9f43', width=1.2), name='Signal'), row=2, col=1)
            
            # MACD Hist bars with conditional coloring
            hist_colors = ['#ff7b72' if val >= 0 else '#56d364' for val in df['MACD_Hist']]
            fig.add_trace(go.Bar(
                x=df['Date'], 
                y=df['MACD_Hist'], 
                marker_color=hist_colors, 
                name='Histogram',
                showlegend=False
            ), row=2, col=1)
            
            # 3. RSI on Row 3
            fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#00d2d3', width=1.5), name='RSI'), row=3, col=1)
            
            # Add threshold lines to RSI
            fig.add_shape(type="line", x0=df['Date'].iloc[0], y0=70, x1=df['Date'].iloc[-1], y1=70,
                          line=dict(color="red", width=1, dash="dash"), row=3, col=1)
            fig.add_shape(type="line", x0=df['Date'].iloc[0], y0=30, x1=df['Date'].iloc[-1], y1=30,
                          line=dict(color="green", width=1, dash="dash"), row=3, col=1)
                          
            fig.update_layout(
                template="plotly_dark",
                height=800,
                xaxis_rangeslider_visible=False,
                margin=dict(l=50, r=50, t=30, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_yaxes(title_text="股價", row=1, col=1)
            fig.update_yaxes(title_text="MACD", row=2, col=1)
            fig.update_yaxes(title_text="RSI (14)", range=[10, 90], row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # AI Technical Interpretation (Built-in Rules)
            latest_rsi = df['RSI'].iloc[-1]
            latest_macd_hist = df['MACD_Hist'].iloc[-1]
            prev_macd_hist = df['MACD_Hist'].iloc[-2] if len(df) > 1 else 0
            
            st.subheader("💡 技術指標即時解讀")
            col_rsi, col_macd = st.columns(2)
            
            with col_rsi:
                st.markdown("### 🔹 RSI 指標解讀")
                if latest_rsi > 70:
                    st.error(f"目前 RSI 為 **{latest_rsi:.2f}**，處於 **超買區 (RSI > 70)**。市場情緒過熱，短線面臨修正拉回風險，不建議強行追高。")
                elif latest_rsi < 30:
                    st.success(f"目前 RSI 為 **{latest_rsi:.2f}**，處於 **超賣區 (RSI < 30)**。市場情緒悲觀，籌碼相對乾淨，可能迎來跌深反彈，適合中長線分批佈局。")
                else:
                    st.info(f"目前 RSI 為 **{latest_rsi:.2f}**，處於 **常態區 (30 - 70)**。目前股價無極度超買或超賣現象，行情以區間震盪整理為主。")
                    
            with col_macd:
                st.markdown("### 🔹 MACD 指標解讀")
                if latest_macd_hist >= 0 and prev_macd_hist < 0:
                    st.success(f"MACD 柱狀體翻紅，最新值為 **{latest_macd_hist:.4f}**。MACD 完成 **黃金交叉**，暗示短期上漲動能轉強，多頭占據優勢。")
                elif latest_macd_hist < 0 and prev_macd_hist >= 0:
                    st.error(f"MACD 柱狀體翻綠，最新值為 **{latest_macd_hist:.4f}**。MACD 完成 **死亡交叉**，短期下跌動能增強，宜做好部位避險。")
                elif latest_macd_hist >= 0:
                    st.info(f"MACD 柱狀體為正數 (**{latest_macd_hist:.4f}**)。多頭行情仍屬強勢，只要紅柱沒有持續縮水，波段上攻格局未變。")
                else:
                    st.info(f"MACD 柱狀體為負數 (**{latest_macd_hist:.4f}**)。空頭盤整趨勢持續中，建議靜待綠柱收斂或翻紅後再行介入。")
        else:
            st.warning("查無技術指標資料。")

# ==========================================
# PAGE 5: 財經新聞整合 & AI 摘要
# ==========================================
elif choice == "📰 財經新聞 & AI 摘要":
    st.markdown("<h1 class='title-gradient'>📰 財經新聞 & AI 摘要</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>抓取即時財經新聞，並透過 OpenAI GPT 提供利多、利空與風險摘要解讀</p>", unsafe_allow_html=True)
    
    # Check OpenAI availability status
    is_available = api_get("/api/search", params={"q": "2330"}) # Quick health check is fine
    
    st.markdown("""
    > 💡 **使用說明**：在下方新聞列表中，點擊新聞卡片右側的 **🤖 AI 一鍵分析** 按鈕，系統將會將該篇新聞全文發送給 AI 進行利多利空整理與投資結論摘要。
    """)
    
    news_res = api_get("/api/news")
    if news_res and news_res.get("news"):
        for idx, news in enumerate(news_res["news"]):
            st.markdown("---")
            # Side-by-side layout: news details on left, AI button & analysis on right
            c1, c2 = st.columns([3, 2])
            
            with c1:
                st.markdown(f"### <a href='{news['link']}' target='_blank' style='text-decoration: none; color: #58a6ff;'>{news['title']}</a>", unsafe_allow_html=True)
                st.caption(f"發布時間：{news['pub_date']}")
                st.write(news['content'])
                
            with c2:
                # Unique state for each news analysis output
                ai_key = f"ai_summary_{idx}"
                if ai_key not in st.session_state:
                    st.session_state[ai_key] = None
                    
                if st.button(f"🤖 AI 一鍵分析", key=f"btn_{idx}", use_container_width=True):
                    with st.spinner("AI 正在解析新聞全文..."):
                        summary_res = api_post("/api/news/summarize", json_data={
                            "title": news["title"],
                            "content": news["content"]
                        })
                        if summary_res and summary_res.get("summary"):
                            st.session_state[ai_key] = summary_res["summary"]
                        else:
                            st.error("AI 摘要生成失敗")
                            
                # Show report output if it exists in state
                if st.session_state[ai_key]:
                    st.markdown(st.session_state[ai_key])
    else:
        st.info("暫無即時新聞。")

# ==========================================
# PAGE 6: 個人關注清單
# ==========================================
elif choice == "⭐ 個人關注清單":
    st.markdown("<h1 class='title-gradient'>⭐ 個人關注清單</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-gradient'>追蹤收藏股票/ETF的即時價格表現，並繪製整體報酬率比較圖</p>", unsafe_allow_html=True)
    
    # Watchlist table
    watchlist_res = api_get("/api/watchlist")
    if watchlist_res and watchlist_res.get("watchlist"):
        watchlist = watchlist_res["watchlist"]
        
        # Display as DataFrame
        df_list = []
        for item in watchlist:
            change_pct = item["change_percent"]
            sign = "+" if change_pct and change_pct >= 0 else ""
            
            df_list.append({
                "證券代碼": item["code"],
                "證券名稱": item["name"],
                "市場類型": item["market_type"],
                "產業別": item["industry_type"],
                "最新收盤": item["price"],
                "漲跌幅 (%)": f"{sign}{change_pct:.2f}%" if change_pct is not None else "N/A",
                "本益比": round(item["pe_ratio"], 2) if item["pe_ratio"] is not None else "N/A",
                "殖利率": f"{item['dividend_yield']*100:.2f}%" if item["dividend_yield"] is not None else "N/A"
            })
            
        watchlist_df = pd.DataFrame(df_list)
        st.dataframe(watchlist_df, use_container_width=True, hide_index=True)
        
        # Watchlist actions - let user delete
        st.write("")
        st.subheader("⚙️ 關注清單管理")
        delete_codes = [item["code"] for item in watchlist]
        delete_labels = [f"{item['code']} - {item['name']}" for item in watchlist]
        
        c_del_select, c_del_btn = st.columns([4, 1])
        with c_del_select:
            to_delete_label = st.selectbox("選擇要移出的證券", delete_labels)
        with c_del_btn:
            st.write("") # padding
            if st.button("🗑️ 確認移出", use_container_width=True):
                to_delete_code = to_delete_label.split(" - ")[0]
                if api_delete(f"/api/watchlist/remove/{to_delete_code}"):
                    st.success(f"已移出 {to_delete_code}")
                    st.rerun()
                    
        # Visual Comparison of watchlisted stocks
        st.write("")
        st.subheader("📈 關注清單報酬率走勢對比 (近3個月)")
        
        with st.spinner("載入報酬率比較數據中..."):
            fig = go.Figure()
            has_data = False
            
            for item in watchlist:
                code = item["code"]
                hist_res = api_get(f"/api/stock/{code}/history", params={"period": "3mo"})
                if hist_res and hist_res.get("history"):
                    df_h = pd.DataFrame(hist_res["history"])
                    if not df_h.empty:
                        # Calculate cumulative return: (Close / First Close - 1) * 100
                        first_close = df_h['Close'].iloc[0]
                        df_h['Cum_Return'] = ((df_h['Close'] / first_close) - 1) * 100
                        
                        fig.add_trace(go.Scatter(
                            x=df_h['Date'],
                            y=df_h['Cum_Return'],
                            mode='lines',
                            name=f"{item['name']} ({code})"
                        ))
                        has_data = True
                        
            if has_data:
                fig.update_layout(
                    title="累計報酬率比較 (%)",
                    xaxis_title="日期",
                    yaxis_title="累計報酬率 (%)",
                    template="plotly_dark",
                    height=450,
                    margin=dict(l=50, r=30, t=40, b=40)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暫無足夠的歷史股價資料繪製報酬率比較圖。")
    else:
        st.info("您的關注清單目前是空的。請至股票資料查詢或首頁儀表板將證券加入關注！")
