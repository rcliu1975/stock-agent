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

## 安裝

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 快速開始

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

不送 Telegram：

```bash
python3 main.py --config config/config_tw.yaml --no-telegram
```

暫時覆蓋股票池與報告筆數：

```bash
python3 main.py --config config/config_tw.yaml --offline --symbols 2330.TW,2454.TW --top-n 2
```

## CLI 參數

- `--config`：指定 YAML 設定檔，必填
- `--offline`：強制使用內建樣本資料，不連外抓行情
- `--no-telegram`：停用 Telegram 發送
- `--symbols`：以逗號分隔的 symbol 清單，覆蓋設定檔股票池
- `--top-n`：覆蓋報告輸出筆數

## 腳本

`scripts/run_tw_daily.sh`

- 用途：執行台股每日報告
- 用法：`bash scripts/run_tw_daily.sh --offline --no-telegram`

`scripts/run_us_daily.sh`

- 用途：執行美股每日報告
- 用法：`bash scripts/run_us_daily.sh --offline --no-telegram`

`scripts/show_pipeline_status.py`

- 用途：查看最近 pipeline run 與最新 signals
- 用法：`python3 scripts/show_pipeline_status.py --db data/stock_agent.sqlite --market TW --limit 5`

`scripts/backup_sqlite.sh`

- 用途：在大量回填前備份 SQLite
- 用法：`bash scripts/backup_sqlite.sh`

`scripts/backfill_history.py`

- 用途：安全回填 `daily_prices` 與 `technical_indicators`
- 用法：`python3 scripts/backfill_history.py --config config/config_tw.yaml --start-date 2025-01-01 --end-date 2025-12-31 --symbols 2330.TW --chunk-size-days 90 --dry-run`

`scripts/show_backfill_status.py`

- 用途：查看 `backfill_checkpoints` 最新狀態與摘要
- 用法：`python3 scripts/show_backfill_status.py --db data/stock_agent.sqlite --market TW --symbol 2330.TW --limit 10`

`scripts/backfill_signals.py`

- 用途：用既有 `daily_prices`、`technical_indicators`、`fundamentals` 回填歷史 `signals`
- 用法：`python3 scripts/backfill_signals.py --config config/config_tw.yaml --start-date 2025-01-01 --end-date 2025-03-31 --symbols 2330.TW`

`scripts/backfill_tw_market_batches.py`

- 用途：依 `stocks` 資料表分批回填台股市場資料，可選擇是否同時回填歷史 `signals`
- 用法：`python3 scripts/backfill_tw_market_batches.py --config config/config_tw.yaml --start-date 2025-01-01 --end-date 2025-12-31 --batch-size 25 --company-limit 0 --etf-limit 0 --include-signals`

`scripts/plan_tw_backfill.py`

- 用途：檢查目前 active universe 與 DB 覆蓋範圍，並產生 Phase 1 / Phase 2 的建議回填命令
- 用法：`python3 scripts/plan_tw_backfill.py --config config/config_tw.yaml --years 1 --batch-size 25 --company-limit 50 --etf-limit 20 --include-signals`

`scripts/check_tw_readiness.py`

- 用途：在正式跑大規模回填前，檢查 active companies / ETFs / watchlist / DB 覆蓋狀態
- 用法：`python3 scripts/check_tw_readiness.py --config config/config_tw.yaml --min-active-companies 50 --min-active-etfs 20 --min-watchlist-size 70`

`scripts/run_tw_phase1_check.sh`

- 用途：把 Phase 1 的 readiness、plan、dry-run 串成一支預檢腳本
- 用法：`bash scripts/run_tw_phase1_check.sh`

`scripts/sync_tw_universe.py`

- 用途：從 `FinMind` `TaiwanStockInfo` 同步台股股票池與基本 metadata 到 SQLite
- 用法：`python3 scripts/sync_tw_universe.py --config config/config_tw.yaml --exchanges twse,tpex --exclude-industries ETF,上櫃ETF,ETN --stock-id-pattern '^\\d{4}$'`

`scripts/build_tw_watchlist.py`

- 用途：從 DB 的 `daily_prices` 建立「前 50 大個股 + 前 20 大 ETF」追蹤名單 snapshot
- 用法：`python3 scripts/build_tw_watchlist.py --config config/config_tw.yaml --companies 50 --etfs 20 --lookback-days 20`

`scripts/show_watchlist.py`

- 用途：查看最新 watchlist snapshot
- 用法：`python3 scripts/show_watchlist.py --db data/stock_agent.sqlite --market TW --strategy tw_top_companies_etfs`

`scripts/run_tw_automation.sh`

- 用途：每日自動流程，包含備份、同步台股 universe、補近期資料、重建 watchlist、產生日報
- 用法：`bash scripts/run_tw_automation.sh`

`scripts/install_tw_systemd_user.sh`

- 用途：安裝 `systemd --user` 版本的台股每日排程
- 用法：`bash scripts/install_tw_systemd_user.sh`

`scripts/run_tw_maintenance.sh`

- 用途：每 2 小時做一次 database 整理與近期資料收集
- 用法：`bash scripts/run_tw_maintenance.sh`

`scripts/install_tw_maintenance_systemd_user.sh`

- 用途：安裝 `systemd --user` 版本的 TW maintenance timer，每 2 小時跑一次
- 用法：`bash scripts/install_tw_maintenance_systemd_user.sh`

## 設定檔說明

主要欄位如下：

- `market`：市場代碼，例如 `TW`、`US`
- `market_name`：報告顯示名稱
- `currency`：幣別
- `timezone`：市場時區
- `database_path`：SQLite 路徑
- `log_dir`：log 輸出目錄
- `universe.symbols`：股票池
- `data_sources`：資料來源定義
- `technical_indicators`：均線與 RSI 參數
- `score_weights`：三大類評分權重
- `report.output_dir`：報告輸出位置
- `report.telegram_enabled`：是否啟用 Telegram
- `report.top_n`：報告保留筆數

## 資料流程

每次執行的流程如下：

1. 讀取設定檔與 CLI 覆蓋參數
2. 初始化 SQLite schema
3. 逐檔抓取價格資料
4. 計算最新技術指標
5. 補入基本面、新聞與社群樣本資料
6. 計算投機股、成長股、績優股分數
7. 寫入 `signals` 與 `pipeline_runs`
8. 產生 Markdown 報告
9. 依設定決定是否送出 Telegram

## SQLite 資料表

目前會建立以下資料表：

- `stocks`
- `daily_prices`
- `technical_indicators`
- `fundamentals`
- `news_items`
- `social_items`
- `signals`
- `pipeline_runs`

`pipeline_runs` 用來追蹤每次執行的：

- `status`
- `processed_count`
- `success_count`
- `failed_count`
- `report_path`
- `error_summary`

## 輸出內容

- 報告：`reports/daily/<timestamp>_<market>_report.md`
- 資料庫：`data/stock_agent.sqlite`
- Log：`logs/<market>.log`

## 環境變數

若要發送 Telegram，需要設定：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

若後續要接 FinMind，先準備：

- `FINMIND_API_TOKEN`

未設定時會自動跳過 Telegram 發送，不會中斷 pipeline。

`main.py` 與 `scripts/backfill_history.py` 會自動載入 repo 根目錄下的 `.env`。

## 測試

執行全部測試：

```bash
python3 -m unittest discover -s tests -v
```

目前測試覆蓋：

- 指標計算
- pipeline 離線流程
- 單一 symbol 失敗時的容錯
- CLI 覆蓋參數
- 歷史回填 chunk 與離線回填
- `FinMind` symbol mapping 與股票池過濾

## 歷史回填

建議順序：

1. 先備份 SQLite
2. 先用單一 symbol + 小日期區間 + `--dry-run`
3. 驗證 chunk 與預計筆數合理後，再正式寫入
4. 先補 `daily_prices` / `technical_indicators`，不要混入 `signals` 與新聞社群

建議命令：

```bash
bash scripts/backup_sqlite.sh
python3 scripts/backfill_history.py \
  --config config/config_tw.yaml \
  --start-date 2025-01-01 \
  --end-date 2025-03-31 \
  --symbols 2330.TW \
  --chunk-size-days 30 \
  --dry-run
```

正式回填：

```bash
python3 scripts/backfill_history.py \
  --config config/config_tw.yaml \
  --start-date 2025-01-01 \
  --end-date 2025-03-31 \
  --symbols 2330.TW \
  --chunk-size-days 30
```

若要為回測準備歷史選股結果，再跑：

```bash
python3 scripts/backfill_signals.py \
  --config config/config_tw.yaml \
  --start-date 2025-01-01 \
  --end-date 2025-03-31
```

注意：

- 這個歷史 `signals` 回填版本只使用當日以前可得的價格、指標、基本面
- 不納入新聞與社群熱度，避免未來資訊洩漏
- 因此它是較適合回測的基礎版訊號，不是完整即時版訊號

若你要安全分批補「完整市場歷史資料」，可直接用：

```bash
python3 scripts/backfill_tw_market_batches.py \
  --config config/config_tw.yaml \
  --start-date 2024-01-01 \
  --end-date 2026-05-04 \
  --batch-size 25 \
  --company-limit -1 \
  --etf-limit -1 \
  --include-signals
```

建議實務分段：

1. 先 `--company-limit 50 --etf-limit 20`
2. 確認 DB、checkpoint、signals 正常
3. 再改成 `-1/-1` 補完整市場

建議在回填完近期資料後，建立追蹤名單 snapshot：

```bash
python3 scripts/build_tw_watchlist.py \
  --config config/config_tw.yaml \
  --companies 50 \
  --etfs 20 \
  --lookback-days 20
```

目前 `config/config_tw.yaml` 已改成：

- `stocks` metadata 保留全市場資料於資料庫
- pipeline 實際追蹤 universe 優先使用 DB 內最新 `watchlist_snapshots`
- 若尚未建立 snapshot，才退回手動 `symbols`

## 建議頻率

建議每日跑 1 次就夠：

- 時間：台北時間 `15:50`
- 原因：
  - 收盤資料通常已穩定
  - 可同一次完成近期補資料、重建 watchlist、輸出報告
  - 不需要盤中頻繁重跑

若你要更保守：

- 每日 `15:50` 跑一次主流程
- 每週一再額外手動跑一次較長區間 backfill，補漏資料

## 自動化流程

`scripts/run_tw_automation.sh` 預設會做：

1. 若 SQLite 存在，先備份
2. 同步全市場台股 metadata 到 `stocks`
3. 回填最近 `45` 天價格與技術指標
4. 依 DB 建立最新「前 50 大個股 + 前 20 大 ETF」watchlist
5. 產生每日報告

`scripts/run_tw_maintenance.sh` 預設會做：

1. 同步全市場台股 metadata 與 active universe
2. 回填最近 `7` 天價格與技術指標
3. 重建 watchlist
4. 執行 SQLite `ANALYZE`
5. 若 `ENABLE_VACUUM=1` 才額外執行 `VACUUM`

可用環境變數調整：

- `BACKFILL_DAYS`
- `WATCHLIST_LOOKBACK_DAYS`
- `WATCHLIST_COMPANIES`
- `WATCHLIST_ETFS`
- `REPORT_TOP_N`
- `NO_TELEGRAM=1`
- `OFFLINE=1`

例如：

```bash
NO_TELEGRAM=1 BACKFILL_DAYS=60 bash scripts/run_tw_automation.sh
```

## systemd

可用 user-level `systemd`，不需要 root：

```bash
bash scripts/install_tw_systemd_user.sh
systemctl --user list-timers stock-agent-tw-daily.timer
```

預設排程：

```text
Mon..Fri 15:50
```

如要改時間，可在安裝前指定：

```bash
ON_CALENDAR='Mon..Fri 16:10' bash scripts/install_tw_systemd_user.sh
```

## 每兩小時維護

若你想每兩小時自動做一次 database 整理與資料收集，用：

```bash
bash scripts/install_tw_maintenance_systemd_user.sh
systemctl --user list-timers stock-agent-tw-maintenance.timer
```

預設排程：

```text
*-*-* 00/2:00:00
```

手動執行：

```bash
bash scripts/run_tw_maintenance.sh
```

回填腳本特性：

- 每個 chunk 會寫入 `backfill_checkpoints`
- 已完成 chunk 預設會自動跳過
- `--no-resume` 可強制重跑所有 chunk
- `--dry-run` 只驗證與計數，不寫 `daily_prices` / `technical_indicators`
- `dry-run` checkpoint 會標記為 `dry_run`，不會被當成正式成功 chunk 跳過

## 已知限制

- 台股真實資料目前尚未接 FinMind / TWSE，仍以 `yfinance` 或內建樣本為主
- 台股價格來源已可切到 `FinMind`，失敗時會退回 `yfinance`
- 基本面、新聞、社群資料目前多數是內建樣本
- AI 摘要目前是規則式文字，不是外部 LLM
- 還沒有排程器與自動告警整合
- 美股設定檔目前只是共用流程入口，尚未做市場特化

## 下一步建議

- 串接 FinMind / TWSE 真實台股資料
- 加入 `.env.example` 與 API 設定管理
- 補上每日排程與失敗通知
- 擴充新聞與社群來源
- 將報告改成更細的 ranking 與事件區塊

## FinMind 整合

目前台股設定檔預設：

```yaml
data_sources:
  price: finmind
  fundamentals: finmind
```

實作狀態：

- `price: finmind`
  - TW 市場會優先打 `FinMind` `TaiwanStockPrice`
  - 失敗時退回 `yfinance`
- `fundamentals: finmind`
  - 目前先使用 `FinMind` `TaiwanStockPER` 補 `dividend_yield`
  - 其他欄位仍與內建樣本併用

官方參考：

- FinMind `TaiwanStockPrice` 文件：<https://finmind.github.io/tutor/TaiwanMarket/Technical/>
- FinMind quick start：<https://finmind.github.io/quickstart/>
