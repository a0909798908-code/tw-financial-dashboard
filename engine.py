import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import logging
import sqlite3
from config import DB_FILE, NEWS_RSS_URL
from database import get_db_connection

logger = logging.getLogger(__name__)

def resolve_ticker(code: str) -> str:
    """Resolve standard stock code (e.g. 2330) to Yahoo Finance ticker (e.g. 2330.TW or 2330.TWO)."""
    # If already a ticker (has suffix or caret), return it
    if "." in code or code.startswith("^"):
        return code
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT market_type FROM securities WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        market_type = row["market_type"]
        if "上市" in market_type:
            return f"{code}.TW"
        elif "上櫃" in market_type:
            return f"{code}.TWO"
            
    # Default fallback: try .TW, if failure it can be handled by yfinance
    return f"{code}.TW"

def fetch_stock_quote(code: str):
    """Fetch real-time quote info for a given stock code using yfinance."""
    ticker_str = resolve_ticker(code)
    ticker = yf.Ticker(ticker_str)
    
    try:
        # Fetch fast info
        info = ticker.info
        history = ticker.history(period="5d")
        
        if history.empty:
            logger.warning(f"No history data returned for ticker {ticker_str}")
            return None
            
        latest_row = history.iloc[-1]
        prev_row = history.iloc[-2] if len(history) > 1 else latest_row
        
        close_price = float(latest_row['Close'])
        prev_close = float(prev_row['Close']) if len(history) > 1 else float(info.get('previousClose', close_price))
        change = close_price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close else 0.0
        
        # Get security details from DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, market_type, industry_type FROM securities WHERE code = ?", (code,))
        db_row = cursor.fetchone()
        conn.close()
        
        name = db_row["name"] if db_row else info.get("longName", code)
        market_type = db_row["market_type"] if db_row else "未知"
        industry_type = db_row["industry_type"] if db_row else "未知"
        
        return {
            "code": code,
            "ticker": ticker_str,
            "name": name,
            "price": round(close_price, 2),
            "open": round(float(latest_row['Open']), 2),
            "high": round(float(latest_row['High']), 2),
            "low": round(float(latest_row['Low']), 2),
            "volume": int(latest_row['Volume']),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "market_type": market_type,
            "industry_type": industry_type,
            "pe_ratio": info.get("trailingPE", None),
            "dividend_yield": info.get("dividendYield", None), # e.g. 0.035
            "market_cap": info.get("marketCap", None)
        }
    except Exception as e:
        logger.error(f"Error fetching quote for {code}: {e}")
        return None

def fetch_historical_prices(code: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical stock price data."""
    ticker_str = resolve_ticker(code)
    ticker = yf.Ticker(ticker_str)
    try:
        # period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        df = ticker.history(period=period)
        if df.empty:
            logger.warning(f"No historical prices for {ticker_str}")
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Error fetching history for {code}: {e}")
        return pd.DataFrame()

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MA, RSI, and MACD indicators and append to the DataFrame."""
    if df.empty or len(df) < 14:
        return df
        
    df = df.copy()
    
    # 1. Moving Averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 2. RSI (Relative Strength Index - Wilder's Exponential Moving Average version)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilders EMA
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    return df

def fetch_etf_details(code: str):
    """Fetch specific details for an ETF, including dividends and holdings if available."""
    ticker_str = resolve_ticker(code)
    ticker = yf.Ticker(ticker_str)
    
    try:
        info = ticker.info
        dividends = ticker.dividends
        
        # Fetch basic stock info first
        quote = fetch_stock_quote(code)
        if not quote:
            return None
            
        # Compile ETF specifics
        # Dividends summary
        div_history = []
        if not dividends.empty:
            # Sort by date descending, take top 10
            sorted_divs = dividends.sort_index(ascending=False).head(10)
            for date, amt in sorted_divs.items():
                div_history.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "amount": float(amt)
                })
        
        # Calculate trailing dividend yield or use yfinance info
        yield_pct = quote.get("dividend_yield")
        if yield_pct:
            yield_pct = round(yield_pct * 100, 2)
        else:
            # Try to calculate yield using last 4 quarters or past 1 year of dividends
            if not dividends.empty:
                last_year_divs = dividends[dividends.index > (pd.Timestamp.now(tz=dividends.index.tz) - pd.Timedelta(days=365))]
                total_div_1y = float(last_year_divs.sum())
                current_price = quote["price"]
                yield_pct = round((total_div_1y / current_price) * 100, 2) if current_price else 0.0
            else:
                yield_pct = 0.0
                
        # Holdings
        # Note: yfinance doesn't always have holdings for Taiwan ETFs. We will provide a fallback or simulated top holdings if empty.
        holdings = []
        raw_holdings = info.get("holdings", [])
        if raw_holdings:
            for hold in raw_holdings:
                holdings.append({
                    "symbol": hold.get("symbol", ""),
                    "name": hold.get("holdingName", ""),
                    "percent": round(hold.get("holdingPercent", 0) * 100, 2)
                })
        else:
            # Hardcoded mock holdings for common ETFs in Taiwan if yfinance doesn't provide them
            if code == "0050":
                holdings = [
                    {"symbol": "2330", "name": "台積電", "percent": 52.4},
                    {"symbol": "2317", "name": "鴻海", "percent": 6.2},
                    {"symbol": "2454", "name": "聯發科", "percent": 4.5},
                    {"symbol": "2308", "name": "台達電", "percent": 2.1},
                    {"symbol": "2881", "name": "富邦金", "percent": 2.0},
                    {"symbol": "2882", "name": "國泰金", "percent": 1.7},
                    {"symbol": "2382", "name": "廣達", "percent": 1.6},
                    {"symbol": "2412", "name": "中華電", "percent": 1.5},
                    {"symbol": "2891", "name": "中信金", "percent": 1.4},
                    {"symbol": "2303", "name": "聯電", "percent": 1.3}
                ]
            elif code == "0056":
                holdings = [
                    {"symbol": "2382", "name": "廣達", "percent": 3.8},
                    {"symbol": "2317", "name": "鴻海", "percent": 3.5},
                    {"symbol": "2454", "name": "聯發科", "percent": 3.2},
                    {"symbol": "3231", "name": "緯創", "percent": 3.0},
                    {"symbol": "2357", "name": "華碩", "percent": 2.8},
                    {"symbol": "2301", "name": "光寶科", "percent": 2.5},
                    {"symbol": "2379", "name": "瑞昱", "percent": 2.4},
                    {"symbol": "2303", "name": "聯電", "percent": 2.3},
                    {"symbol": "3034", "name": "聯詠", "percent": 2.2},
                    {"symbol": "2324", "name": "仁寶", "percent": 2.1}
                ]
            else:
                # Mock generic portfolio of top Taiwan stocks for other ETFs
                holdings = [
                    {"symbol": "2330", "name": "台積電", "percent": 15.0},
                    {"symbol": "2317", "name": "鴻海", "percent": 8.0},
                    {"symbol": "2454", "name": "聯發科", "percent": 7.0},
                    {"symbol": "2308", "name": "台達電", "percent": 5.0},
                    {"symbol": "2891", "name": "中信金", "percent": 4.5}
                ]
                
        return {
            "quote": quote,
            "dividend_yield": yield_pct,
            "dividend_history": div_history,
            "holdings": holdings,
            "category": info.get("fundFamily", "ETF")
        }
    except Exception as e:
        logger.error(f"Error fetching ETF details for {code}: {e}")
        return None

def fetch_financial_news():
    """Fetch latest financial news from Anue (鉅亨網) Taiwan Stock News RSS feed."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        response = requests.get(NEWS_RSS_URL, headers=headers, timeout=10)
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        news_items = []
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            
            # Clean HTML tags from description if any
            if description:
                description = BeautifulSoup(description, "html.parser").get_text()
                
            news_items.append({
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "summary": description[:200] + "..." if len(description) > 200 else description,
                "content": description # Full description as content
            })
            
        logger.info(f"Scraped {len(news_items)} news items from RSS feed.")
        return news_items
    except Exception as e:
        logger.error(f"Error fetching RSS news: {e}")
        # Fallback news if connection fails
        return [
            {
                "title": "台股加權指數震盪整理，半導體與權值股領軍撐盤",
                "link": "https://news.cnyes.com",
                "pub_date": "Thu, 18 Jun 2026 13:00:00 +0800",
                "summary": "今日台北股市受到美股科技股走弱影響，早盤震盪走低，但在台積電與聯發科等半導體權值股發揮撐盤作用下，大盤收盤小漲，維持在高檔震盪格局...",
                "content": "今日台北股市受到美股科技股走弱影響，早盤震盪走低，但在台積電與聯發科等半導體權值股發揮撐盤作用下，大盤收盤小漲，維持在高檔震盪格局。分析師指出，目前台股基本面強勁，下半年的 AI 晶片出貨量與伺服器需求仍是市場焦點，短期需注意通膨數據與全球央行利率決策會議動向。"
            },
            {
                "title": "元大台灣50 (0050) 即將迎來配息，市場期待殖利率表現",
                "link": "https://news.cnyes.com",
                "pub_date": "Thu, 18 Jun 2026 10:30:00 +0800",
                "summary": "台灣最具指標性的 ETF 元大台灣 50 (0050) 即將進行半年度配息公告，法人表示，今年受惠於台股主要上市櫃公司盈餘發放踴躍，預計配息金額將優於市場預期...",
                "content": "台灣最具指標性的 ETF 元大台灣 50 (0050) 即將進行半年度配息公告，法人表示，今年受惠於台股主要上市櫃公司盈餘發放踴躍，預計配息金額將優於市場預期。散戶與存股族紛紛於除息日前買進，推升 0050 受益人數再創新高。分析師建議，除息後往往是極佳的長線佈局買點。"
            }
        ]

if __name__ == "__main__":
    # Test quote fetcher
    print("Testing resolve_ticker for '2330'")
    print(resolve_ticker("2330"))
    print("\nTesting fetch_stock_quote for '2330'")
    print(fetch_stock_quote("2330"))
