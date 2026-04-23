import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.daily_reporter import DailyReporter


def test_generate_daily_report():
    reporter = DailyReporter()
    report_content = reporter.generate_report(
        date_str="2026-04-15", pnl=-200.0, evolution_reason="Reduced contrarian weight."
    )

    assert "2026-04-15" in report_content
    assert "-200.0" in report_content
    assert "Reduced contrarian" in report_content
