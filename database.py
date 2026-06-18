import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import os
import logging
from config import DB_FILE, TWSE_LIST_URL, TPEX_LIST_URL, DEFAULT_WATCHLIST

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create securities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS securities (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        market_type TEXT,
        industry_type TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create watchlist table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (code) REFERENCES securities (code)
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def scrape_securities_list(url):
    """Scrapes TWSE/TPEx JSP page and returns list of securities dicts."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        # TWSE uses MS950 / CP950 / BIG5 encoding
        response.encoding = 'big5-hkscs' if 'big5' in response.headers.get('Content-Type', '').lower() else 'cp950'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # The table on this page doesn't have class sometimes, but it's typically the only table with list contents
        table = soup.find('table', class_='h4')
        if not table:
            table = soup.find('table')
            
        if not table:
            logger.warning(f"Could not find table on page: {url}")
            return []
            
        rows = table.find_all('tr')
        securities = []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            
            # The first cell contains code and name, like "2330　台積電" (separated by full-width space)
            first_text = cells[0].get_text().strip()
            
            # Split by full-width space (\u3000) or multiple spaces
            parts = re.split(r'[\s\u3000]+', first_text)
            if len(parts) < 2:
                continue
                
            code = parts[0].strip()
            name = parts[1].strip()
            
            # Filter out elements that aren't stocks or ETFs
            # Stocks and ETFs have typical codes (e.g. 4-6 digits, or starting with digits). 
            # Warrants usually have longer, complex codes (e.g. 03001Q, 70001P etc. or length >= 6 with specific prefix)
            # We want to keep:
            # - 4-digit stock codes (e.g. 2330, 2454)
            # - 5 or 6 digit ETF codes (e.g. 0050, 0056, 00878, 00919, 00940)
            if not (code.isalnum() and len(code) >= 4 and len(code) <= 6):
                continue
                
            market_type = cells[3].get_text().strip()
            industry_type = cells[4].get_text().strip()
            
            securities.append({
                'code': code,
                'name': name,
                'market_type': market_type,
                'industry_type': industry_type
            })
            
        logger.info(f"Successfully scraped {len(securities)} securities from {url}")
        return securities
    except Exception as e:
        logger.error(f"Error scraping securities list from {url}: {e}")
        return []

def sync_securities():
    """Sync securities list from TWSE and TPEx to database."""
    logger.info("Starting securities synchronization...")
    twse_securities = scrape_securities_list(TWSE_LIST_URL)
    tpex_securities = scrape_securities_list(TPEX_LIST_URL)
    
    all_securities = twse_securities + tpex_securities
    
    if not all_securities:
        logger.warning("No securities scraped. Sync aborted.")
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Use INSERT OR REPLACE to insert or update existing records
        cursor.executemany("""
        INSERT OR REPLACE INTO securities (code, name, market_type, industry_type, updated_at)
        VALUES (:code, :name, :market_type, :industry_type, CURRENT_TIMESTAMP)
        """, all_securities)
        
        conn.commit()
        logger.info(f"Successfully synchronized {len(all_securities)} securities into database.")
        
        # Add default watchlist items if watchlist is empty
        cursor.execute("SELECT COUNT(*) FROM watchlist")
        count = cursor.fetchone()[0]
        if count == 0:
            for code in DEFAULT_WATCHLIST:
                # check if code exists in securities table
                cursor.execute("SELECT code FROM securities WHERE code = ?", (code,))
                if cursor.fetchone():
                    cursor.execute("INSERT OR IGNORE INTO watchlist (code) VALUES (?)", (code,))
            conn.commit()
            logger.info("Watchlist initialized with default securities.")
            
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to sync securities to database: {e}")
        return False
    finally:
        conn.close()

def search_securities(query: str, limit: int = 15):
    """Search securities by code or name (fuzzy search)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try exact match first
    cursor.execute("""
    SELECT code, name, market_type, industry_type 
    FROM securities 
    WHERE code = ?
    """, (query,))
    exact = cursor.fetchone()
    
    if exact:
        conn.close()
        return [dict(exact)]
        
    # Then fuzzy match
    like_query = f"%{query}%"
    cursor.execute("""
    SELECT code, name, market_type, industry_type 
    FROM securities 
    WHERE code LIKE ? OR name LIKE ?
    ORDER BY 
        CASE 
            WHEN code LIKE ? THEN 1 
            WHEN name LIKE ? THEN 2
            ELSE 3 
        END, code ASC
    LIMIT ?
    """, (like_query, like_query, f"{query}%", f"{query}%", limit))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_watchlist():
    """Retrieve all securities in the watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.code, s.name, s.market_type, s.industry_type, w.created_at
    FROM watchlist w
    JOIN securities s ON w.code = s.code
    ORDER BY w.created_at DESC
    """)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def add_to_watchlist(code: str):
    """Add a security code to the watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First ensure it exists in securities
        cursor.execute("SELECT code FROM securities WHERE code = ?", (code,))
        if not cursor.fetchone():
            conn.close()
            return False, "Security code not found in database. Please sync or try another."
            
        cursor.execute("INSERT OR IGNORE INTO watchlist (code) VALUES (?)", (code,))
        conn.commit()
        conn.close()
        return True, "Added to watchlist successfully."
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        conn.close()
        return False, str(e)

def remove_from_watchlist(code: str):
    """Remove a security code from the watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return True, "Removed from watchlist successfully."
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        conn.close()
        return False, str(e)

if __name__ == "__main__":
    init_db()
    sync_securities()
