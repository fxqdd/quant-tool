from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = DATA_DIR / "output"

DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

AKSHARE_CONFIG = {
    "stock_list": ["000001", "600519", "000858"],
    "index_list": ["000001", "399001", "399006"],
    "start_date": "20240101",
    "end_date": "20260331",
}

SENTIMENT_CONFIG = {
    "xueqiu_enabled": False,
    "eastmoney_enabled": False,
    "timeout": 30,
}

BACKTEST_CONFIG = {
    "initial_capital": 1000000,
    "commission": 0.0003,
    "slippage": 0.0001,
    "stop_loss": 0.05,
    "take_profit": 0.10,
}
