from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: str, market: str) -> Path:
    folder = Path(log_dir)
    folder.mkdir(parents=True, exist_ok=True)
    log_path = folder / f"{market.lower()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_path

