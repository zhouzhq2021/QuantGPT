#!/usr/bin/env python3
"""Audit local prewarm coverage without contacting remote data sources."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from quantgpt.fundamental_data import FUNDAMENTAL_VARIABLES  # noqa: E402
from quantgpt.market_data import get_universe  # noqa: E402

START = pd.Timestamp("2018-01-01")
END = pd.Timestamp("2025-12-31")
FUND_DIR = PROJECT_ROOT / "data" / "fundamentals"
MARKET_DIR = PROJECT_ROOT / "data" / "stocks"
DIV_DIR = PROJECT_ROOT / "data" / "dividends"


def _codes(name: str) -> list[str]:
    return list(dict.fromkeys(get_universe(name, date=START.strftime("%Y-%m-%d"))))


def _fundamental_coverage(codes: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in FUNDAMENTAL_VARIABLES}
    for code in codes:
        path = FUND_DIR / f"{code.replace('.', '_')}.parquet"
        if not path.exists():
            continue
        try:
            frame = pd.read_parquet(path)
        except Exception:
            continue
        if "stat_date" not in frame or frame.empty:
            continue
        dates = pd.to_datetime(frame["stat_date"], errors="coerce").dropna()
        # Match FundamentalDataFetcher._cache_complete() boundary tolerance.
        if dates.empty or dates.min() > START - pd.Timedelta("265D") or dates.max() < END - pd.Timedelta("100D"):
            continue
        for name in counts:
            if name in frame and pd.to_numeric(frame[name], errors="coerce").notna().any():
                counts[name] += 1
    return counts


def _market_coverage(codes: list[str]) -> int:
    covered = 0
    for code in codes:
        path = MARKET_DIR / f"{code.replace('.', '_')}.parquet"
        try:
            frame = pd.read_parquet(path)
            dates = pd.to_datetime(frame["trade_date"], errors="coerce").dropna()
            if not dates.empty and dates.min() <= START + pd.Timedelta("5D") and dates.max() >= END - pd.Timedelta("5D"):
                covered += 1
        except Exception:
            pass
    return covered


def main() -> int:
    report = {"range": [START.date().isoformat(), END.date().isoformat()], "universes": {}}
    failures = []
    for universe in ("hs300", "csi500"):
        codes = _codes(universe)
        fundamental = _fundamental_coverage(codes)
        market = _market_coverage(codes)
        dividends = sum((DIV_DIR / f"{code.replace('.', '_')}.parquet").exists() for code in codes)
        report["universes"][universe] = {
            "stocks": len(codes),
            "market_complete": market,
            "fundamentals": fundamental,
            "dividend_files": dividends,
        }
        for field, count in fundamental.items():
            if count < len(codes):
                failures.append(f"{universe}:{field} {count}/{len(codes)}")
        if market < len(codes):
            failures.append(f"{universe}:market {market}/{len(codes)}")

    out = PROJECT_ROOT / "logs" / "prewarm_coverage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print("INCOMPLETE: " + "; ".join(failures))
        return 1
    print("READY: all audited fields and market ranges are locally covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
