#!/usr/bin/env python3
"""
Pre-warm all data caches for QuantGPT.

Usage:
    python scripts/prewarm.py [--universe all|hs300|csi500|csi1000|csi2000]
                               [--start 2015-01-01] [--end 2025-12-31]
                               [--skip-market] [--skip-fundamentals] [--skip-dividends]

Run on server:
    nohup python scripts/prewarm.py > /tmp/prewarm.log 2>&1 &
"""

import argparse
from contextlib import contextmanager
import fcntl
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("prewarm")

START_DATE = "2015-01-01"
END_DATE = "2025-12-31"

UNIVERSES = ["hs300", "csi500", "csi1000", "csi2000"]
BENCHMARKS = ["hs300", "zz500", "csi1000"]


@contextmanager
def _prewarm_lock():
    """Allow only one prewarm process to use remote data at a time."""
    lock_path = Path(__file__).resolve().parent.parent / "data" / ".prewarm.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise RuntimeError("another prewarm process is already running") from e
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def prewarm_universe_lists(universes: list[str]):
    """Cache universe constituent lists for current month."""
    from quantgpt.market_data import get_universe
    for name in universes:
        try:
            codes = get_universe(name)
            logger.info(f"Universe {name}: {len(codes)} stocks cached")
        except Exception as e:
            logger.error(f"Universe {name} failed: {e}")


def prewarm_benchmarks(benchmarks: list[str]):
    """Cache benchmark return series."""
    from quantgpt.market_data import fetch_benchmark_returns
    for bm in benchmarks:
        try:
            ret = fetch_benchmark_returns(bm, START_DATE, END_DATE)
            if ret is not None:
                logger.info(f"Benchmark {bm}: {len(ret)} days cached")
            else:
                logger.warning(f"Benchmark {bm}: no data returned")
        except Exception as e:
            logger.error(f"Benchmark {bm} failed: {e}")


def prewarm_market_data(stock_codes: list, batch_size: int = 100, pause_seconds: float = 1.0):
    """Cache OHLCV data for all stocks in batches."""
    from quantgpt.market_data import MarketDataFetcher
    fetcher = MarketDataFetcher()
    total = len(stock_codes)
    logger.info(f"Pre-warming market data for {total} stocks ({START_DATE} ~ {END_DATE})")

    for i in range(0, total, batch_size):
        batch = stock_codes[i:i + batch_size]
        try:
            df = fetcher.fetch_stocks(batch, START_DATE, END_DATE)
            n = df["stock_code"].nunique() if df is not None else 0
            logger.info(f"Market data batch {i//batch_size + 1}: {n}/{len(batch)} stocks loaded ({i+len(batch)}/{total} total)")
            if i + len(batch) < total and pause_seconds > 0:
                time.sleep(pause_seconds)
        except Exception as e:
            logger.error(f"Market data batch {i//batch_size + 1} failed: {e}")


def prewarm_fundamentals(stock_codes: list, batch_size: int = 10, pause_seconds: float = 2.0):
    """Cache fundamental data for all stocks."""
    from quantgpt.fundamental_data import FundamentalDataFetcher, ALL_FUNDAMENTAL_NAMES
    from quantgpt.market_data import CACHE_ONLY, _baostock_login, _baostock_logout
    fetcher = FundamentalDataFetcher()
    total = len(stock_codes)
    if not CACHE_ONLY:
        # Validate the source once. Without this guard every batch would repeat
        # the same login failure and make a large prewarm look stuck.
        try:
            _baostock_login()
        except Exception as e:
            logger.error(f"Fundamental source unavailable; skipping remote prewarm: {e}")
            return
        finally:
            _baostock_logout()
    # Use all fundamental vars to ensure all columns are cached
    needed_vars = set(ALL_FUNDAMENTAL_NAMES) - {"dividend_yield"}  # dividend handled separately
    logger.info(f"Pre-warming fundamentals for {total} stocks ({len(needed_vars)} vars)")

    for i in range(0, total, batch_size):
        batch = stock_codes[i:i + batch_size]
        try:
            df = fetcher.fetch_fundamentals(batch, START_DATE, END_DATE, needed_vars)
            n = df["stock_code"].nunique() if df is not None else 0
            logger.info(f"Fundamentals batch {i//batch_size + 1}: {n}/{len(batch)} stocks ({i+len(batch)}/{total} total)")
            if i + len(batch) < total and pause_seconds > 0:
                time.sleep(pause_seconds)
        except Exception as e:
            logger.error(f"Fundamentals batch {i//batch_size + 1} failed: {e}")


def prewarm_dividends(stock_codes: list, batch_size: int = 10, pause_seconds: float = 2.0):
    """Cache dividend data for all stocks."""
    from quantgpt.fundamental_data import FundamentalDataFetcher
    fetcher = FundamentalDataFetcher()
    total = len(stock_codes)
    logger.info(f"Pre-warming dividends for {total} stocks")

    for i in range(0, total, batch_size):
        batch = stock_codes[i:i + batch_size]
        try:
            df = fetcher.fetch_dividend_data(batch, START_DATE, END_DATE)
            n = df["stock_code"].nunique() if df is not None else 0
            logger.info(f"Dividends batch {i//batch_size + 1}: {n}/{len(batch)} stocks ({i+len(batch)}/{total} total)")
            if i + len(batch) < total and pause_seconds > 0:
                time.sleep(pause_seconds)
        except Exception as e:
            logger.error(f"Dividends batch {i//batch_size + 1} failed: {e}")


def main():
    global START_DATE, END_DATE
    parser = argparse.ArgumentParser(description="Pre-warm QuantGPT data caches")
    parser.add_argument("--universe", default="all", help="Universe to warm: all|hs300|csi500|csi1000|csi2000")
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--skip-fundamentals", action="store_true")
    parser.add_argument("--skip-dividends", action="store_true")
    parser.add_argument("--skip-factors", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10, help="Stocks per remote batch (default: 10)")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds between remote batches (default: 2)")
    args = parser.parse_args()

    START_DATE = args.start
    END_DATE = args.end

    # Load .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")
    if args.pause < 0:
        parser.error("--pause must be >= 0")

    logger.info("=== QuantGPT Data Pre-warm ===")
    logger.info(f"Date range: {START_DATE} ~ {END_DATE}")

    # Step 1: Cache universe lists
    logger.info("--- Step 1: Universe constituent lists ---")
    universes_to_warm = UNIVERSES if args.universe == "all" else [args.universe]
    prewarm_universe_lists(universes_to_warm)

    # Step 2: Collect all stock codes
    logger.info("--- Step 2: Collecting all stock codes ---")
    from quantgpt.market_data import get_universe
    all_codes = set()
    for name in universes_to_warm:
        try:
            codes = get_universe(name)
            all_codes.update(codes)
            logger.info(f"  {name}: {len(codes)} stocks")
        except Exception as e:
            logger.error(f"  {name} failed: {e}")
    stock_codes = sorted(all_codes)
    logger.info(f"Total unique stocks: {len(stock_codes)}")

    # Step 3: Benchmark data
    logger.info("--- Step 3: Benchmark data ---")
    benchmark_names = [name for name in BENCHMARKS if name in ("hs300", "zz500", "csi1000")]
    if args.universe != "all":
        benchmark_names = {
            "hs300": ["hs300"],
            "csi500": ["zz500"],
            "csi1000": ["csi1000"],
            "csi2000": ["hs300", "zz500", "csi1000"],
        }.get(args.universe, [])
    prewarm_benchmarks(benchmark_names)

    # Step 4: Market OHLCV data
    if not args.skip_market:
        logger.info("--- Step 4: Market OHLCV data ---")
        prewarm_market_data(stock_codes, args.batch_size * 10, args.pause)
    else:
        logger.info("--- Step 4: Market OHLCV data (SKIPPED) ---")

    # Step 5: Fundamental data (baostock quarterly)
    if not args.skip_fundamentals:
        logger.info("--- Step 5: Fundamental data (baostock) ---")
        prewarm_fundamentals(stock_codes, args.batch_size, args.pause)
    else:
        logger.info("--- Step 5: Fundamental data (SKIPPED) ---")

    # Step 6: Dividend data (baostock)
    if not args.skip_dividends:
        logger.info("--- Step 6: Dividend data (baostock) ---")
        prewarm_dividends(stock_codes, args.batch_size, args.pause)
    else:
        logger.info("--- Step 6: Dividend data (SKIPPED) ---")

    # Step 7: rqdatac daily factors (ROE, PE, PB, etc.)
    if not args.skip_factors:
        logger.info("--- Step 7: rqdatac daily factors ---")
        try:
            from quantgpt.fundamental_data import prewarm_factors_rq
            from quantgpt.market_data import enable_rqdatac
            with enable_rqdatac():
                prewarm_factors_rq(stock_codes, START_DATE, END_DATE)
        except Exception as e:
            logger.error(f"Factor prewarm failed: {e}")

    logger.info("=== Pre-warm complete ===")


if __name__ == "__main__":
    try:
        with _prewarm_lock():
            main()
    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(2)
