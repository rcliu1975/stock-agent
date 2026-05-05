import unittest

from src.core.report import render_telegram_html


class ReportTests(unittest.TestCase):
    def test_render_telegram_html_escapes_and_formats_summary(self):
        config = {"market_name": "Taiwan Stock Market", "market": "TW"}
        ranked_rows = [
            {
                "symbol": "2330.TW",
                "category": "成長股",
                "speculation_score": 71.23,
                "growth_score": 88.12,
                "quality_score": 76.45,
                "action": "BUY",
                "confidence_score": 82.5,
                "stop_loss": 88.0,
                "reason": "成長股分數最高；<測試>",
                "warning": "RSI 偏高 & 留意",
            }
        ]
        message = render_telegram_html(config, "2026-05-05", ranked_rows, failures=["2454.TW: bad <data>"])
        self.assertIn("<b>Taiwan Stock Market 每日股票報告</b>", message)
        self.assertIn("<code>2330.TW</code> 買進 成長股", message)
        self.assertIn("信心 82.50 / 停損 88.00", message)
        self.assertIn("成長股分數最高；&lt;測試&gt;", message)
        self.assertIn("2454.TW: bad &lt;data&gt;", message)


if __name__ == "__main__":
    unittest.main()
