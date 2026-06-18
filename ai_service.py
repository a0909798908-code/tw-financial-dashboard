import os
import logging
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Initialize OpenAI Client if key is provided
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
else:
    logger.warning("OPENAI_API_KEY not found. AI service will run in Mock/Simulation mode.")

def is_ai_available() -> bool:
    """Returns True if OpenAI API is configured and available."""
    return client is not None

def generate_mock_analysis(text_type: str, title: str) -> str:
    """Generates simulated financial analysis when API key is missing."""
    return f"""### 🤖 [模擬 AI 分析模式 - 請配置 OpenAI API 金鑰]

**本分析報告由模擬 AI 引擎生成。要啟用完整 GPT 分析，請在 `.env` 中設定 `OPENAI_API_KEY`。**

#### 📌 1. 新聞重點
- 本次事件為「{title}」，引起市場廣泛關注。
- 晶片製造與半導體供應鏈板塊交易量明顯放大，法人籌碼略有異動。
- 技術面仍處於均線之上，中長線趨勢方向依舊由偏多方掌控。

#### 📈 2. 利多因素
- **產業需求強勁**：下半年度終端消費電子市場回溫，晶圓代工與先進封裝產能利用率持續看漲。
- **基本面護城河**：該龍頭企業在先進製程擁有技術壟斷性，定價權穩固，毛利率預期維持在 53% 以上高檔。

#### 📉 3. 利空因素
- **匯率波動風險**：近期新台幣與美元走勢劇烈，出口商恐面臨短線匯兌收益縮水的挑戰。
- **評價面偏高**：短期股價漲幅已反映未來數季營收，目前本益比接近歷史區間上緣，獲利回吐賣壓蠢蠢欲動。

#### ⚠️ 4. 風險提醒
- **地緣政治干擾**：全球科技冷戰加劇，需密切注意國際對半導體出口管制的政策變化。
- **供應鏈瓶頸**：CoWoS 等先進封裝設備交期拉長，可能稍微壓抑第三季出貨量成長的爆發力。

#### 💡 5. 簡短結論
綜合而言，此事件對市場長期走勢屬於中性偏多。建議短線投資人切勿過度追高，可等待股價拉回至月線或季線支撐處分批佈局；長期投資人則可續抱以參與產業循環增長红利。
"""

def analyze_news_ai(title: str, content: str) -> str:
    """Analyze news article and extract key items."""
    if not is_ai_available():
        return generate_mock_analysis("news", title)
        
    try:
        prompt = f"""請針對以下財經新聞進行深度分析，並依規定格式以繁體中文(zh-TW)輸出：
新聞標題：{title}
新聞內容：{content}
"""
        
        system_msg = (
            "你是一位資深的台灣證券分析師。請仔細閱讀新聞，並整理出該事件對相關股票或市場的影響。\n"
            "你的輸出必須是 Markdown 格式，且必須嚴格包含以下標題與內容：\n"
            "#### 📌 1. 新聞重點\n"
            "#### 📈 2. 利多因素\n"
            "#### 📉 3. 利空因素\n"
            "#### ⚠️ 4. 風險提醒\n"
            "#### 💡 5. 簡短結論\n"
            "請以專業、客觀、條理分明的金融口吻撰寫，適合一般投資人閱讀。"
        )
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API for news analysis: {e}")
        return f"AI 分析失敗: {str(e)}\n\n" + generate_mock_analysis("news", title)

def get_ai_investment_report(stock_code: str, stock_name: str, quote_data: dict, history_summary: str) -> str:
    """Generate a custom investment report using stock metrics."""
    if not is_ai_available():
        return generate_mock_analysis("report", f"{stock_code} {stock_name} 投資分析報告")
        
    try:
        prompt = f"""請為這檔台灣證券生成投資分析報告：
證券代碼：{stock_code}
證券名稱：{stock_name}
即時行情：價格={quote_data.get('price')}, 漲跌幅={quote_data.get('change_percent')}%, 成交量={quote_data.get('volume')}
市場與產業：市場類型={quote_data.get('market_type')}, 產業別={quote_data.get('industry_type')}, 本益比={quote_data.get('pe_ratio')}, 殖利率={quote_data.get('dividend_yield')}
歷史股價走勢簡述：{history_summary}
"""
        
        system_msg = (
            "你是一位頂尖的股票投資顧問。請根據提供的數據，為該證券撰寫一份繁體中文(zh-TW)投資分析報告。\n"
            "請將內容整理成：\n"
            "#### 📌 1. 股票資訊摘要 (簡述其目前的市場地位、交易熱度)\n"
            "#### 📈 2. 利多因素 (包括財報亮點、技術均線支撐或產業趨勢)\n"
            "#### 📉 3. 利空因素 (如估值偏高、交易量萎縮、籌碼面警訊等)\n"
            "#### ⚠️ 4. 風險提醒 (包括行業競爭、大盤修正、法說會變數等)\n"
            "#### 💡 5. 簡短結論 (具體的長短期投資策略建議)"
        )
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API for report: {e}")
        return f"AI 報告生成失敗: {str(e)}\n\n" + generate_mock_analysis("report", f"{stock_code} {stock_name}")

def ai_chat_assistant(query: str, context: str = "") -> str:
    """A natural language helper to answer financial or code-specific questions."""
    if not is_ai_available():
        return "🤖 [模擬AI] 您好！要使用真正的 AI 對話助手，請配置您的 `OPENAI_API_KEY`。目前為模擬回應：建議您注意技術面上收盤價突破均線的買點，並控制好部位風險。"
        
    try:
        system_msg = (
            "你是一位親切且專業的 AI 理財助理，專門解答台灣股市、ETF、技術指標及大盤趨勢的相關問題。\n"
            "請用繁體中文回答，口吻需親切有禮，多用條列式說明，並在文末加上風險警語。"
        )
        messages = [
            {"role": "system", "content": system_msg}
        ]
        if context:
            messages.append({"role": "system", "content": f"目前上下文資訊：\n{context}"})
        messages.append({"role": "user", "content": query})
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API for chat: {e}")
        return f"AI 助手錯誤: {str(e)}"
