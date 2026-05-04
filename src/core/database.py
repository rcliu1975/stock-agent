from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS stocks (
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

CREATE TABLE IF NOT EXISTS daily_prices (
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

CREATE TABLE IF NOT EXISTS technical_indicators (
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

CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    period TEXT NOT NULL,
    eps REAL,
    revenue_yoy REAL,
    roe REAL,
    gross_margin REAL,
    debt_ratio REAL,
    free_cash_flow REAL,
    dividend_yield REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, period)
);

CREATE TABLE IF NOT EXISTS news_items (
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

CREATE TABLE IF NOT EXISTS social_items (
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

CREATE TABLE IF NOT EXISTS signals (
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
    reason TEXT,
    warning TEXT,
    ai_summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market, signal_date)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    run_date TEXT NOT NULL,
    status TEXT NOT NULL,
    processed_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    report_path TEXT,
    error_summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def upsert_stock(connection: sqlite3.Connection, stock: dict) -> None:
    connection.execute(
        """
        INSERT INTO stocks(symbol, name, market, exchange, industry, currency)
        VALUES (:symbol, :name, :market, :exchange, :industry, :currency)
        ON CONFLICT(symbol, market) DO UPDATE SET
            name=excluded.name,
            exchange=excluded.exchange,
            industry=excluded.industry,
            currency=excluded.currency,
            is_active=1
        """,
        stock,
    )


def upsert_price_rows(connection: sqlite3.Connection, rows: Iterable[dict]) -> None:
    connection.executemany(
        """
        INSERT INTO daily_prices(symbol, market, trade_date, open, high, low, close, volume, turnover)
        VALUES (:symbol, :market, :trade_date, :open, :high, :low, :close, :volume, :turnover)
        ON CONFLICT(symbol, market, trade_date) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume,
            turnover=excluded.turnover
        """,
        rows,
    )


def upsert_indicator(connection: sqlite3.Connection, row: dict) -> None:
    connection.execute(
        """
        INSERT INTO technical_indicators(
            symbol, market, trade_date, ma5, ma20, ma60, ma120, rsi14, volume_ma5, volume_ma20,
            high_20d, low_20d, high_52w, low_52w
        )
        VALUES (
            :symbol, :market, :trade_date, :ma5, :ma20, :ma60, :ma120, :rsi14, :volume_ma5, :volume_ma20,
            :high_20d, :low_20d, :high_52w, :low_52w
        )
        ON CONFLICT(symbol, market, trade_date) DO UPDATE SET
            ma5=excluded.ma5,
            ma20=excluded.ma20,
            ma60=excluded.ma60,
            ma120=excluded.ma120,
            rsi14=excluded.rsi14,
            volume_ma5=excluded.volume_ma5,
            volume_ma20=excluded.volume_ma20,
            high_20d=excluded.high_20d,
            low_20d=excluded.low_20d,
            high_52w=excluded.high_52w,
            low_52w=excluded.low_52w
        """,
        row,
    )


def upsert_fundamental(connection: sqlite3.Connection, row: dict) -> None:
    connection.execute(
        """
        INSERT INTO fundamentals(
            symbol, market, period, eps, revenue_yoy, roe, gross_margin, debt_ratio, free_cash_flow, dividend_yield
        )
        VALUES (
            :symbol, :market, :period, :eps, :revenue_yoy, :roe, :gross_margin, :debt_ratio, :free_cash_flow, :dividend_yield
        )
        ON CONFLICT(symbol, market, period) DO UPDATE SET
            eps=excluded.eps,
            revenue_yoy=excluded.revenue_yoy,
            roe=excluded.roe,
            gross_margin=excluded.gross_margin,
            debt_ratio=excluded.debt_ratio,
            free_cash_flow=excluded.free_cash_flow,
            dividend_yield=excluded.dividend_yield
        """,
        row,
    )


def insert_news(connection: sqlite3.Connection, rows: Iterable[dict]) -> None:
    connection.executemany(
        """
        INSERT INTO news_items(symbol, market, title, url, source, published_at, raw_text)
        VALUES (:symbol, :market, :title, :url, :source, :published_at, :raw_text)
        """,
        rows,
    )


def insert_social(connection: sqlite3.Connection, rows: Iterable[dict]) -> None:
    connection.executemany(
        """
        INSERT INTO social_items(symbol, market, platform, title, content, url, author, published_at, likes, comments)
        VALUES (:symbol, :market, :platform, :title, :content, :url, :author, :published_at, :likes, :comments)
        """,
        rows,
    )


def upsert_signal(connection: sqlite3.Connection, row: dict) -> None:
    connection.execute(
        """
        INSERT INTO signals(
            symbol, market, signal_date, category, speculation_score, growth_score, quality_score,
            social_heat_score, sentiment_score, risk_score, reason, warning, ai_summary
        )
        VALUES (
            :symbol, :market, :signal_date, :category, :speculation_score, :growth_score, :quality_score,
            :social_heat_score, :sentiment_score, :risk_score, :reason, :warning, :ai_summary
        )
        ON CONFLICT(symbol, market, signal_date) DO UPDATE SET
            category=excluded.category,
            speculation_score=excluded.speculation_score,
            growth_score=excluded.growth_score,
            quality_score=excluded.quality_score,
            social_heat_score=excluded.social_heat_score,
            sentiment_score=excluded.sentiment_score,
            risk_score=excluded.risk_score,
            reason=excluded.reason,
            warning=excluded.warning,
            ai_summary=excluded.ai_summary
        """,
        row,
    )


def insert_pipeline_run(connection: sqlite3.Connection, row: dict) -> None:
    connection.execute(
        """
        INSERT INTO pipeline_runs(
            market, run_date, status, processed_count, success_count, failed_count, report_path, error_summary
        )
        VALUES (
            :market, :run_date, :status, :processed_count, :success_count, :failed_count, :report_path, :error_summary
        )
        """,
        row,
    )
