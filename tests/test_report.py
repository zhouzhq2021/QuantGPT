"""Tests for WQ summary report generation."""

from pathlib import Path

from quantgpt.report import generate_wq_summary_report


def test_generate_wq_summary_report_escapes_and_renders(tmp_path):
    result = {
        "alpha_id": "alpha-1",
        "wq_brain": {
            "wq_rating": "A", "wq_sharpe": 1.8, "wq_fitness": 1.1,
            "wq_returns": 0.12, "wq_turnover": 0.3,
        },
        "is_metrics": {
            "checks": [{"name": "LOW_FITNESS", "result": "PASS", "value": 1.1, "limit": 1.0}],
        },
        "settings": {"region": "USA"},
    }
    report = generate_wq_summary_report(
        "rank(close < open)", result,
        interpretation={"logic": "真实 LLM 分析", "suggestions": ["继续验证"]},
        output_dir=str(tmp_path),
    )
    content = Path(report["report_path"]).read_text(encoding="utf-8")
    assert "WQ Metrics" in content
    assert "真实 LLM 分析" in content
    assert "rank(close &lt; open)" in content
    assert "LOW_FITNESS" in content
