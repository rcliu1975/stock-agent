# stock-agent

`stock-agent` 是一個可執行的股票篩選 MVP，先以台股流程為主，提供：

- 以設定檔驅動的市場分析流程
- SQLite 資料庫初始化與寫入
- pipeline run 紀錄與 log 檔
- 價格資料蒐集，支援 `yfinance` 與內建 fallback 樣本
- 技術指標、三類評分、每日 Markdown 報告
- 可選 Telegram 發送

## 專案結構

```text
stock-agent/
├── main.py
├── config/
├── data/
├── reports/daily/
├── scripts/
├── src/
└── tests/
```

## 安裝

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方式

台股每日分析：

```bash
python3 main.py --config config/config_tw.yaml
```

美股測試流程：

```bash
python3 main.py --config config/config_us.yaml
```

強制使用內建樣本資料：

```bash
python3 main.py --config config/config_tw.yaml --offline
```

只產生報告、不送 Telegram：

```bash
python3 main.py --config config/config_tw.yaml --no-telegram
```

## 腳本

`scripts/run_tw_daily.sh`

- 用途：執行台股每日報告
- 用法：`bash scripts/run_tw_daily.sh`

`scripts/run_us_daily.sh`

- 用途：執行美股每日報告
- 用法：`bash scripts/run_us_daily.sh`

`scripts/show_pipeline_status.py`

- 用途：查看最近 pipeline run 與 signals
- 用法：`python3 scripts/show_pipeline_status.py --db data/stock_agent.sqlite --market TW --limit 5`

## 環境變數

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

未設定時會自動跳過 Telegram 發送。

## 執行輸出

- 報告：`reports/daily/*_report.md`
- 資料庫：`data/stock_agent.sqlite`
- Log：`logs/<market>.log`
- 執行紀錄：SQLite `pipeline_runs` table
