import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Database Config
DB_FILE = os.getenv("DB_FILE", "financial_dashboard.db")

# OpenAI Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# News Config
# Anue (鉅亨網) Taiwan stock news RSS feed
NEWS_RSS_URL = "https://news.cnyes.com/rss/category/tw_stock"

# TWSE Securities list JSP URL
TWSE_LIST_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
# TPEx Securities list JSP URL (for Over-the-counter stocks)
TPEX_LIST_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"

# Default watch list (e.g. TAIEX, TSMC, Yuanta 50, etc.)
DEFAULT_WATCHLIST = ["2330", "0050", "0056", "2317", "2454"]
