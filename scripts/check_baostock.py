#!/usr/bin/env python3
"""Probe BaoStock once before a scheduled prewarm."""

import os
import sys
from pathlib import Path


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_env()
    from quantgpt.market_data import _baostock_login, _baostock_logout

    try:
        _baostock_login()
        import baostock as bs

        result = bs.query_profit_data(code="sh.600519", year=2024, quarter=4)
        rows = []
        while result.next() and len(rows) < 1:
            rows.append(result.get_row_data())
        print(f"probe_ok code={result.error_code} rows={len(rows)}")
        return 0 if result.error_code == "0" else 1
    except Exception as exc:
        print(f"probe_failed: {type(exc).__name__}: {exc}")
        return 1
    finally:
        _baostock_logout()


if __name__ == "__main__":
    sys.exit(main())
