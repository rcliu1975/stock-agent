可以。下面我幫你整理成一份 **「股票自動篩選 + AI 社群風向分析工具」開發規畫**。
方向是：**一套核心程式，多個市場設定檔；第一版先做台股，之後再加美股。**

---

# 股票自動篩選工具規畫

## 0. 專案目標

做一個可以每天自動執行的股票分析工具，功能包括：

```text
1. 自動抓股價、成交量、基本面資料
2. 自動計算技術指標
3. 自動分類股票：
   - 投機股
   - 成長股
   - 績優股
4. 自動抓新聞與社群風向
5. 用 AI 摘要事件與市場情緒
6. 每天產生 Markdown / Telegram 報告
7. 所有資料存進 SQLite
8. 後續可擴充成 Web dashboard
```

核心原則：

```text
數字交給程式
文字交給 AI
決策交給人
```

---

# 1. 整體架構

```text
stock-agent/
├── main.py
├── config/
│   ├── config_tw.yaml
│   └── config_us.yaml
│
├── data/
│   └── stock_agent.sqlite
│
├── reports/
│   └── daily/
│
├── logs/
│
├── src/
│   ├── core/
│   │   ├── pipeline.py
│   │   ├── database.py
│   │   ├── indicators.py
│   │   ├── scoring.py
│   │   ├── report.py
│   │   └── scheduler.py
│   │
│   ├── markets/
│   │   ├── base.py
│   │   ├── tw.py
│   │   └── us.py
│   │
│   ├── collectors/
│   │   ├── finmind.py
│   │   ├── twse.py
│   │   ├── yfinance_collector.py
│   │   ├── news.py
│   │   └── social.py
│   │
│   ├── ai/
│   │   ├── sentiment.py
│   │   ├── event_summary.py
│   │   └── prompts.py
│   │
│   └── notify/
│       └── telegram.py
│
├── scripts/
│   ├── run_tw_daily.sh
│   └── run_us_daily.sh
│
├── requirements.txt
└── README.md
```

---

# 2. 核心設計：共用程式，分開設定

## 共用部分

這些台股、美股都共用：

```text
資料庫
技術指標計算
分數計算框架
報告產生器
Telegram 通知
AI 摘要流程
log 系統
排程系統
```

## 分開部分

這些用設定檔控制：

```text
市場代號
資料來源
股票清單
交易時間
幣別
漲跌停規則
基本面資料欄位
社群來源
評分權重
AI prompt
報告發送時間
```

---

# 3. 設定檔範例

## config/config_tw.yaml

```yaml
market: TW
market_name: Taiwan Stock Market
currency: TWD
timezone: Asia/Taipei

universe:
  source: twse
  include:
    - listed
    - otc
  exclude:
    - etf
    - warrant

data_sources:
  price: finmind
  monthly_revenue: finmind
  institutional: finmind
  fundamentals: finmind
  news: rss
  social:
    - ptt
    - yahoo_finance
    - youtube

rules:
  has_price_limit: true
  has_monthly_revenue: true
  has_institutional_trading: true
  has_premarket: false

technical_indicators:
  moving_average:
    - 5
    - 20
    - 60
    - 120
  rsi_period: 14
  volume_ma:
    - 5
    - 20

score_weights:
  speculation:
    price_breakout: 25
    volume_breakout: 25
    institutional_buying: 20
    social_heat: 20
    limit_up_signal: 10

  growth:
    monthly_revenue_yoy: 35
    eps_growth: 25
    gross_margin: 15
    roe: 15
    price_trend: 10

  quality:
    roe_stability: 25
    dividend_stability: 25
    free_cash_flow: 20
    debt_ratio: 15
    drawdown_control: 15

report:
  language: zh-TW
  output_dir: reports/daily
  telegram_enabled: true
  send_time: "15:30"

ai:
  enabled: true
  analyze_top_n: 30
  model: gpt-5.5-thinking
```

## config/config_us.yaml

第二階段再做：

```yaml
market: US
market_name: US Stock Market
currency: USD
timezone: America/New_York

data_sources:
  price: yfinance
  fundamentals: fmp
  filings: sec
  news: rss
  social:
    - reddit
    - stocktwits
    - youtube

rules:
  has_price_limit: false
  has_monthly_revenue: false
  has_institutional_trading: false
  has_premarket: true

score_weights:
  speculation:
    price_breakout: 20
    volume_breakout: 20
    premarket_gap: 20
    short_interest: 15
    options_activity: 15
    social_heat: 10

  growth:
    quarterly_revenue_growth: 30
    eps_growth: 25
    gross_margin: 15
    free_cash_flow: 15
    guidance_quality: 15

  quality:
    free_cash_flow: 25
    dividend_history: 20
    buyback: 15
    revenue_stability: 20
    moat_score: 20
```

---

# 4. 資料庫設計 SQLite

## stocks

```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT,
    market TEXT NOT NULL,
    exchange TEXT,
    industry TEXT,
    currency TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market)
);
```

## daily_prices

```sql
CREATE TABLE daily_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    turnover REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, trade_date)
);
```

## technical_indicators

```sql
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ma5 REAL,
    ma20 REAL,
    ma60 REAL,
    ma120 REAL,
    rsi14 REAL,
    volume_ma5 REAL,
    volume_ma20 REAL,
    high_20d REAL,
    low_20d REAL,
    high_52w REAL,
    low_52w REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, trade_date)
);
```

## monthly_revenue

台股第一版很重要。

```sql
CREATE TABLE monthly_revenue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    revenue_month TEXT NOT NULL,
    revenue REAL,
    revenue_yoy REAL,
    revenue_mom REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, revenue_month)
);
```

## fundamentals

```sql
CREATE TABLE fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    period TEXT NOT NULL,
    eps REAL,
    roe REAL,
    gross_margin REAL,
    operating_margin REAL,
    debt_ratio REAL,
    free_cash_flow REAL,
    dividend_yield REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, period)
);
```

## news_items

```sql
CREATE TABLE news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    market TEXT,
    title TEXT NOT NULL,
    url TEXT,
    source TEXT,
    published_at TEXT,
    raw_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## social_items

```sql
CREATE TABLE social_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    market TEXT,
    platform TEXT,
    title TEXT,
    content TEXT,
    url TEXT,
    author TEXT,
    published_at TEXT,
    likes INTEGER,
    comments INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## signals

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    category TEXT,

    speculation_score REAL,
    growth_score REAL,
    quality_score REAL,
    social_heat_score REAL,
    sentiment_score REAL,
    risk_score REAL,

    buy_watch_price REAL,
    stop_loss_price REAL,
    warning_price REAL,

    reason TEXT,
    warning TEXT,
    ai_summary TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, signal_date)
);
```

---

# 5. 三類股票分類規則

## A. 投機股 Speculation

目標：找短線資金、題材、放量突破。

### 指標

```text
價格突破 20 日高點
成交量 > 20 日均量 2 倍
收盤價 > MA5 > MA20
近 5 日漲幅不能過熱
社群熱度上升
新聞事件明確
法人連買
```

### 買入觀察條件

```text
放量突破
隔日不開高走低
站穩突破價
沒有爆量長上影
停損點明確
```

### 小心條件

```text
爆量長上影
跌破 5MA
跌破大量紅 K 低點
社群過熱
利多新聞大量洗版
處置股 / 注意股風險
```

---

## B. 成長股 Growth

目標：找營收、獲利、產業趨勢向上的股票。

### 指標

```text
近 3 個月營收 YoY > 20%
近 4 季 EPS 成長
毛利率穩定或上升
ROE > 15%
股價在 MA60 附近止跌
估值沒有嚴重過熱
```

### 買入觀察條件

```text
回到合理估值區
60MA 附近止跌
營收成長仍在
財報沒有轉弱
產業新聞偏正面
```

### 小心條件

```text
月營收 YoY 連續下滑
毛利率連續下降
EPS 低於預期
股價跌破 120MA
估值過高
法說會語氣保守
```

---

## C. 績優股 Quality

目標：找長期穩定、適合核心持有的股票。

### 指標

```text
ROE 長期穩定
連續多年獲利
配息穩定
現金流穩定
負債比合理
產業地位穩
最大回檔較小
本益比沒有太高
```

### 買入方式

```text
分批買
定期定額
估值低於歷史平均時加碼
大盤恐慌時分批撿
```

### 小心條件

```text
本益比明顯高於歷史區間
EPS 連續衰退
股利政策改變
公司治理事件
產業長期衰退
```

---

# 6. AI 使用設計

AI 不負責直接判斷買賣，只負責整理文字資料。

## AI 負責

```text
新聞摘要
事件分類
社群情緒分析
題材辨識
炒作風險判斷
產生好讀報告
```

## AI 不負責

```text
直接預測股價
決定買賣
取代停損規則
取代基本面計算
取代回測
```

## AI 分析輸入

每檔候選股給 AI 的資料：

```json
{
  "symbol": "2330",
  "name": "台積電",
  "market": "TW",
  "price_signal": {
    "close": 900,
    "volume_ratio": 2.3,
    "above_ma20": true,
    "breakout_20d": true
  },
  "fundamental_signal": {
    "revenue_yoy_3m_avg": 28.5,
    "roe": 24.1,
    "eps_growth": 18.2
  },
  "news": [
    "新聞標題 1",
    "新聞標題 2"
  ],
  "social_posts": [
    "PTT 討論摘要 1",
    "YouTube 留言摘要 2"
  ]
}
```

## AI 輸出格式

```json
{
  "event_type": "AI server demand",
  "sentiment": "positive",
  "social_heat": 82,
  "event_quality": 75,
  "pump_risk": 35,
  "summary": "近期討論主要集中在 AI 伺服器需求，新聞與基本面相關性高，社群偏多但尚未明顯過熱。",
  "warning": "若後續營收未跟上題材，股價可能回檔。"
}
```

---

# 7. 每日報告格式

## Markdown 報告範例

```markdown
# 台股每日自動篩選報告
日期：2026-05-04

## 今日總結

今日共掃描 1800 檔股票。

- 投機股候選：12 檔
- 成長股候選：8 檔
- 績優股候選：15 檔
- 高風險過熱股票：5 檔

---

## 投機股候選

### 1234 XX公司

分數：

- 投機分數：86
- 成長分數：42
- 績優分數：35
- 社群熱度：78
- 風險分數：62

訊號：

- 放量突破 20 日高點
- 成交量為 20 日均量 2.8 倍
- 社群討論量上升
- 有新聞事件支撐

買入觀察：

- 若明日站穩 58.5，可列入短線觀察
- 停損參考：54.2
- 不建議開盤直接追高

AI 摘要：

近期討論集中在 AI 題材與接單消息，社群情緒偏多，但短線漲幅已大，需要注意追高風險。

---

## 成長股候選

### 5678 YY公司

分數：

- 投機分數：45
- 成長分數：89
- 績優分數：70
- 社群熱度：42
- 風險分數：35

成長理由：

- 近 3 個月營收 YoY 平均 31%
- EPS 連續成長
- 毛利率穩定
- 股價回到 60MA 附近

買入觀察：

- 60MA 附近止跌可以分批觀察
- 若跌破 120MA，暫停加碼

---

## 績優股候選

### 9999 ZZ公司

分數：

- 投機分數：20
- 成長分數：58
- 績優分數：93

核心理由：

- ROE 穩定
- 配息穩定
- 現金流穩定
- 波動低於市場平均

買入方式：

- 適合分批
- 估值低於歷史平均時提高買入權重

風險：

- 若本益比高於歷史平均太多，暫停加碼
```

---

# 8. 執行流程

## 每日台股流程

```text
15:00 收盤後
        ↓
抓每日股價
        ↓
更新 SQLite
        ↓
計算技術指標
        ↓
抓月營收 / 基本面 / 法人
        ↓
程式初步篩選候選股
        ↓
只對候選股抓新聞與社群
        ↓
AI 摘要與情緒分析
        ↓
計算最終分數
        ↓
產生 Markdown 報告
        ↓
發 Telegram
```

## 指令

```bash
python main.py --config config/config_tw.yaml
```

或：

```bash
./scripts/run_tw_daily.sh
```

---

# 9. 開發階段規畫

## Phase 1：最小可行版本 MVP

目標：先做出每天能跑的台股篩選器。

功能：

```text
1. 建立專案架構
2. 建立 SQLite schema
3. 抓台股每日股價
4. 計算 MA / RSI / 成交量均線
5. 建立簡單投機股分數
6. 建立簡單成長股分數
7. 建立簡單績優股分數
8. 產生 Markdown 報告
```

暫時不做：

```text
AI
社群
美股
Web dashboard
自動下單
```

第一版重點是先穩定跑起來。

---

## Phase 2：加入台股基本面

功能：

```text
1. 月營收
2. EPS
3. ROE
4. 毛利率
5. 殖利率
6. 本益比
7. 三大法人買賣
```

這一階段可以讓成長股與績優股分類更有意義。

---

## Phase 3：加入 AI 新聞摘要

功能：

```text
1. 抓新聞標題與內文摘要
2. 將候選股送給 AI
3. AI 判斷事件類型
4. AI 產生利多 / 利空摘要
5. AI 產生報告文字
```

先只分析程式篩出的前 20～30 檔，避免成本爆掉。

---

## Phase 4：加入社群風向

功能：

```text
1. 抓 PTT 股票板
2. 抓 Yahoo 股市留言或公開討論
3. 抓 YouTube 標題 / 留言
4. 計算討論量變化
5. AI 判斷情緒與炒作風險
```

輸出：

```text
社群熱度分數
情緒分數
炒作風險分數
題材關鍵字
```

---

## Phase 5：Telegram 自動推播

功能：

```text
1. 每日報告推播
2. 高風險警報
3. 特定股票 watchlist 警報
4. 指令查詢個股
```

例如 Telegram 輸入：

```text
/stock 2330
```

回覆：

```text
2330 台積電
分類：績優 + 成長
今日狀態：站上 20MA
風險：估值偏高
社群風向：中性偏多
```

---

## Phase 6：加入美股

功能：

```text
1. config_us.yaml
2. yfinance price collector
3. 美股財報資料 collector
4. Reddit / Stocktwits 社群
5. SEC filing 摘要
6. 美股專用 scoring weights
```

---

## Phase 7：Web Dashboard

可以用 Streamlit 做：

```text
首頁：今日總覽
個股頁：價格 + 分數 + 新聞 + 社群
分類頁：投機股 / 成長股 / 績優股
Watchlist：自選股
回測頁：策略測試
```

---

# 10. 第一版推薦技術選擇

## Python packages

```text
pandas
numpy
requests
PyYAML
SQLAlchemy
ta
yfinance
beautifulsoup4
feedparser
python-dotenv
python-telegram-bot
APScheduler
```

## requirements.txt 第一版

```txt
pandas
numpy
requests
PyYAML
SQLAlchemy
ta
yfinance
beautifulsoup4
feedparser
python-dotenv
python-telegram-bot
APScheduler
```

---

# 11. 第一版先不要做的事

這些先不要碰，會讓專案爆掉：

```text
自動下單
高頻交易
選擇權分析
太複雜的 AI agent
太多社群平台
完整美股財報分析
即時行情
盤中交易訊號
```

第一版只做：

```text
收盤後分析
每日報告
人工決策
```

這樣穩很多。

---

# 12. MVP 開發順序

我建議照這個順序：

```text
Step 1. 建 repo 與目錄
Step 2. 建 SQLite schema
Step 3. 寫 config loader
Step 4. 寫台股價格 collector
Step 5. 寫 technical indicators
Step 6. 寫 scoring engine
Step 7. 寫 Markdown report
Step 8. 寫 daily runner
Step 9. 加 Telegram
Step 10. 加 AI summary
```

---

# 13. 第一版輸出目標

第一版跑完後，要產生這種檔案：

```text
reports/daily/tw_2026-05-04.md
```

內容包含：

```text
今日總結
投機股 Top 10
成長股 Top 10
績優股 Top 10
高風險警告
資料更新狀態
```

---

# 14. 專案名稱建議

可以叫：

```text
stock-agent
market-screener-agent
tw-stock-agent
ai-stock-screener
```

我比較建議：

```text
stock-agent
```

簡單、以後可以支援台股、美股、ETF。

---

# 15. 最終建議

我會這樣切：

```text
第一階段：台股純程式版
第二階段：台股 + 基本面
第三階段：台股 + AI 新聞摘要
第四階段：台股 + 社群風向
第五階段：Telegram bot
第六階段：美股
第七階段：Web dashboard
```

最小第一版不要太大，先把這條跑通：

```text
抓資料 → 算指標 → 打分數 → 產生報告
```

等這條穩了，再加 AI 和社群。

最重要的設計是：

```text
core engine 共用
market profile 分開
data adapter 分開
score weights 分開
report generator 共用
```

也就是：

> **一套核心引擎，多個市場設定檔。**
