from pathlib import Path

from src.core.cli import main
from src.core.env import load_dotenv


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent)
    raise SystemExit(main())
