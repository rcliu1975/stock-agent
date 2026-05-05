# stock-agent

## 一次安裝後放著跑

如果你的使用情境是：

- 一開始只想跑一次安裝腳本
- 之後讓它自己定時整理資料庫、收集資料、更新追蹤名單
- 平常不太管它
- 有空時再去看每天產生的 Markdown 報告

那就照這個最短流程做。

1. 建立環境並安裝套件

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. 安裝 user mode `systemd` 排程

```bash
bash scripts/install_tw_maintenance_systemd_user.sh
```

3. 確認 timer 已啟用

```bash
systemctl --user list-timers stock-agent-tw-maintenance.timer
```

安裝完成後，`stock-agent` 會每兩小時自動做這些事：

- 同步台股 metadata 與 active universe
- 補最近幾天的價格與技術指標
- 重建 watchlist
- 對 SQLite 執行 `ANALYZE`

如果你還要每天產生一份可閱讀的日報，另外再安裝每日報告 timer：

```bash
bash scripts/install_tw_systemd_user.sh
systemctl --user list-timers stock-agent-tw-daily.timer
```

如果你想從另一台機器或手機遠端瀏覽這些報告，再安裝只讀瀏覽 service：

```bash
HOST=0.0.0.0 PORT=8787 bash scripts/install_report_browser_systemd_user.sh
systemctl --user status stock-agent-report-browser.service
```

如果只在本機打開，保留預設 `HOST=127.0.0.1` 就好。

日報會輸出到：

- `reports/daily/`

檔名格式類似：

- `reports/daily/2026-05-05_tw_report.md`
- `reports/daily/2026-05-05T15-50-00_tw_report.md`

也就是 Markdown `.md` 報告，不是 `.md5`。

你平常只需要偶爾來看：

```bash
ls reports/daily/
```

或直接開最新報告：

```bash
less reports/daily/2026-05-05_tw_report.md
```

如果有啟動報告瀏覽 service，也可以直接用瀏覽器打開：

- `http://127.0.0.1:8787/`
- `http://你的主機IP:8787/`

## 怎麼接 Telegram

如果你想讓日報自動發到 Telegram，先準備兩個環境變數：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

建議直接寫進 repo 根目錄的 `.env`：

```bash
TELEGRAM_BOT_TOKEN=你的 bot token
TELEGRAM_CHAT_ID=你的 chat id
```

`stock-agent` 會自動載入這個 `.env`。

取得方式：

1. `TELEGRAM_BOT_TOKEN`
- 到 Telegram 找 `@BotFather`
- 建立一個 bot
- 取得 bot token

2. `TELEGRAM_CHAT_ID`
- 先私訊你的 bot 一句話
- 再查：

```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"
```

- 在回傳 JSON 裡找 `chat.id`

可先手動測試發送：

```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID" \
  -d "text=stock-agent telegram test"
```

測試成功後，正常執行：

```bash
python3 main.py --config config/config_tw.yaml
```

不要加 `--no-telegram`，它才會送出。

`stock-agent` 是一個以設定檔驅動的股票篩選工具，目前已完成可執行 MVP，先聚焦台股流程，並保留美股設定入口。它的目標不是自動下單，而是每天自動整理可讀的觀察名單，讓數值分析、事件摘要與人工判斷能分開處理。

核心原則：

- 數字交給程式
- 文字交給摘要流程
- 決策交給人

## 目前已完成

- 以 YAML 設定檔驅動市場、股票池與評分權重
- SQLite 自動初始化與資料寫入
- 價格資料抓取，優先使用 `yfinance`，失敗時回退到內建樣本資料
- 技術指標計算：`MA5`、`MA20`、`MA60`、`MA120`、`RSI14`、成交量均線
- 三類評分：投機股、成長股、績優股
- Markdown 每日報告輸出
- Telegram 可選通知
- pipeline run 紀錄與 log 檔
- 單一 symbol 失敗隔離，不會讓整批中斷
- CLI 支援暫時覆蓋 `symbols` 與 `top_n`

## 專案結構

```text
stock-agent/
├── main.py
├── config/
│   ├── config_tw.yaml
│   └── config_us.yaml
├── data/
├── logs/
├── reports/
│   └── daily/
├── scripts/
│   ├── run_tw_daily.sh
│   ├── run_us_daily.sh
│   └── show_pipeline_status.py
├── src/
│   ├── ai/
│   ├── collectors/
│   ├── core/
│   ├── markets/
│   └── notify/
└── tests/
```

## 什麼情境該打什麼指令

詳細指令與完整說明已移到 [Manual.md](/home/roger/WorkSpace/stock-agent/Manual.md)。

- 想快速安裝後放著跑：
  - `bash scripts/install_tw_maintenance_systemd_user.sh`
  - `bash scripts/install_tw_systemd_user.sh`
- 想從手機或另一台電腦遠端看報告：
  - `HOST=0.0.0.0 PORT=8787 bash scripts/install_report_browser_systemd_user.sh`
- 想立刻手動跑一次日報：
  - `python3 main.py --config config/config_tw.yaml`
- 想看最近跑批與 signals：
  - `python3 scripts/show_pipeline_status.py --db data/stock_agent.sqlite --market TW --limit 5`
- 想同步台股股票池與修正 active universe：
  - `python3 scripts/sync_tw_universe.py --config config/config_tw.yaml`
- 想補近期市場資料，讓 watchlist 長大：
  - `python3 scripts/backfill_tw_market_batches.py --config config/config_tw.yaml --start-date 2026-04-01 --end-date 2026-05-05 --batch-size 25 --company-limit 50 --etf-limit 20`
- 想重建「前 50 大公司 + 前 20 大 ETF」追蹤名單：
  - `python3 scripts/build_tw_watchlist.py --config config/config_tw.yaml --companies 50 --etfs 20 --lookback-days 20`
- 想檢查目前資料是否已準備好：
  - `python3 scripts/check_tw_readiness.py --config config/config_tw.yaml --min-active-companies 50 --min-active-etfs 20 --min-watchlist-size 70`
- 想安全試跑歷史回填：
  - `bash scripts/backup_sqlite.sh`
  - `python3 scripts/backfill_history.py --config config/config_tw.yaml --start-date 2025-01-01 --end-date 2025-03-31 --symbols 2330.TW --chunk-size-days 30 --dry-run`
- 想為回測補歷史 signals：
  - `python3 scripts/backfill_signals.py --config config/config_tw.yaml --start-date 2025-01-01 --end-date 2025-03-31`
