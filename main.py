import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

from config import DB_FILE
from database import (
    init_db,
    sync_securities,
    search_securities,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    get_db_connection
)
from engine import (
    fetch_stock_quote,
    fetch_historical_prices,
    calculate_technical_indicators,
    fetch_etf_details,
    fetch_financial_news
)
from ai_service import analyze_news_ai, get_ai_investment_report, ai_chat_assistant

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backend")

app = FastAPI(
    title="Financial Dashboard API Backend",
    description="Backend API for Taiwan Stock and ETF Dashboard, with AI Analysis and Technical Indicators",
    version="1.0.0"
)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class WatchlistRequest(BaseModel):
    code: str

class NewsSummaryRequest(BaseModel):
    title: str
    content: str

class ChatRequest(BaseModel):
    query: str
    context: Optional[str] = ""

@app.on_event("startup")
def startup_event():
    """Run database initialization and check for daily updates on startup."""
    init_db()
    
    import threading
    from datetime import datetime, timedelta
    
    # Check if we need to sync (if count == 0 or last update is older than 24h)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM securities")
    count = cursor.fetchone()[0]
    
    should_sync = False
    if count == 0:
        should_sync = True
    else:
        cursor.execute("SELECT MAX(updated_at) FROM securities")
        max_updated = cursor.fetchone()[0]
        if max_updated:
            try:
                # SQLite timestamp parsing
                last_update = datetime.strptime(max_updated, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_update > timedelta(hours=24):
                    should_sync = True
            except Exception as e:
                logger.error(f"Error parsing database timestamp: {e}")
                should_sync = True
        else:
            should_sync = True
            
    conn.close()
    
    if should_sync:
        logger.info("Securities database is empty or outdated (>24 hours). Starting background synchronization...")
        threading.Thread(target=sync_securities, daemon=True).start()
    else:
        logger.info(f"Securities database is up-to-date ({count} items cached). Ready.")

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Financial Dashboard Backend API is running.",
        "db": DB_FILE
    }

@app.get("/api/sync")
def trigger_sync():
    """Endpoint to manually sync securities list from TWSE/TPEx."""
    success = sync_securities()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to sync securities list from TWSE.")
    return {"status": "success", "message": "Securities database synchronized successfully."}

@app.get("/api/search")
def search(q: str = Query(..., min_length=1)):
    """Search stock/ETF list by code or name."""
    results = search_securities(q)
    return {"results": results}

@app.get("/api/stock/{code}")
def get_stock_quote(code: str):
    """Get real-time quote for a security code."""
    quote = fetch_stock_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Stock quote not found for code: {code}")
    return quote

@app.get("/api/stock/{code}/history")
def get_stock_history(code: str, period: str = "1y"):
    """Get historical prices for a stock code."""
    df = fetch_historical_prices(code, period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No history found for code: {code}")
    
    # Convert dataframe to JSON response list
    df = df.reset_index()
    # Format Date column
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    records = df.to_dict(orient='records')
    return {"code": code, "period": period, "history": records}

@app.get("/api/stock/{code}/technical")
def get_stock_technical(code: str, period: str = "1y"):
    """Get stock history with precalculated technical indicators (MA, RSI, MACD)."""
    df = fetch_historical_prices(code, period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No history found for code: {code}")
    
    df_indicators = calculate_technical_indicators(df)
    df_indicators = df_indicators.reset_index()
    df_indicators['Date'] = df_indicators['Date'].dt.strftime('%Y-%m-%d')
    
    # Convert to dict records and replace any float NaN values with None for JSON compatibility
    records = df_indicators.to_dict(orient='records')
    for r in records:
        for k, v in r.items():
            # Check for float NaN (v != v is True for NaN)
            if isinstance(v, float) and (v != v):
                r[k] = None
                
    return {"code": code, "period": period, "indicators": records}

@app.get("/api/etf/{code}")
def get_etf(code: str):
    """Get ETF information, including holdings and dividend history."""
    details = fetch_etf_details(code)
    if not details:
        raise HTTPException(status_code=404, detail=f"ETF info not found for code: {code}")
    return details

@app.get("/api/news")
def get_news():
    """Get latest financial news articles."""
    news = fetch_financial_news()
    return {"news": news}

@app.post("/api/news/summarize")
def summarize_news(req: NewsSummaryRequest):
    """Use AI to summarize a news article and return bullish/bearish analysis."""
    summary = analyze_news_ai(req.title, req.content)
    return {"summary": summary}

@app.post("/api/ai/report/{code}")
def generate_ai_report(code: str):
    """Generate an AI-driven investment report for a stock code."""
    quote = fetch_stock_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Stock code {code} not found.")
        
    df = fetch_historical_prices(code, period="3mo")
    history_summary = "資料庫無近期股價歷史"
    if not df.empty:
        recent_close = df['Close'].tolist()
        start_price = recent_close[0]
        end_price = recent_close[-1]
        highest = df['High'].max()
        lowest = df['Low'].min()
        pct_change = ((end_price - start_price) / start_price) * 100
        history_summary = f"近三個月收盤價自 {start_price:.2f} 變動至 {end_price:.2f} (變幅 {pct_change:.2f}%)，期間最高點 {highest:.2f}，最低點 {lowest:.2f}。"
        
    report = get_ai_investment_report(code, quote.get("name", code), quote, history_summary)
    return {"code": code, "report": report}

@app.post("/api/ai/chat")
def chat_assistant(req: ChatRequest):
    """Provide natural language financial query interface."""
    answer = ai_chat_assistant(req.query, req.context)
    return {"answer": answer}

@app.get("/api/watchlist")
def view_watchlist():
    """Get all watchlisted stocks with their latest pricing info."""
    watchlist_items = get_watchlist()
    enriched_watchlist = []
    
    for item in watchlist_items:
        code = item["code"]
        quote = fetch_stock_quote(code)
        if quote:
            item.update({
                "price": quote["price"],
                "change": quote["change"],
                "change_percent": quote["change_percent"],
                "volume": quote["volume"],
                "pe_ratio": quote["pe_ratio"],
                "dividend_yield": quote["dividend_yield"]
            })
        else:
            item.update({
                "price": None,
                "change": None,
                "change_percent": None,
                "volume": None,
                "pe_ratio": None,
                "dividend_yield": None
            })
        enriched_watchlist.append(item)
        
    return {"watchlist": enriched_watchlist}

@app.post("/api/watchlist/add")
def add_watchlist_item(req: WatchlistRequest):
    """Add a stock/ETF code to user's watchlist."""
    success, msg = add_to_watchlist(req.code)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

@app.delete("/api/watchlist/remove/{code}")
def remove_watchlist_item(code: str):
    """Remove stock/ETF from user's watchlist."""
    success, msg = remove_from_watchlist(code)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
