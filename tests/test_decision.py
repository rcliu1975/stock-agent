import unittest

from src.core.decision import make_trade_decision


class DecisionTests(unittest.TestCase):
    def test_make_trade_decision_buy(self):
        decision = make_trade_decision(
            latest_price={"close": 100, "volume": 1200},
            indicator={
                "ma5": 101,
                "ma20": 99,
                "ma60": 90,
                "high_20d": 101,
                "low_20d": 92,
                "rsi14": 60,
                "volume_ma20": 1000,
            },
            scores={"speculation_score": 80, "growth_score": 76, "quality_score": 74, "risk_score": 35},
        )
        self.assertEqual(decision.action, "BUY")
        self.assertGreaterEqual(decision.confidence_score, 80)
        self.assertEqual(decision.entry_price, 100)
        self.assertLess(decision.stop_loss, decision.entry_price)
        self.assertGreater(decision.take_profit, decision.entry_price)

    def test_make_trade_decision_sell_on_broken_trend(self):
        decision = make_trade_decision(
            latest_price={"close": 80, "volume": 900},
            indicator={
                "ma5": 84,
                "ma20": 90,
                "ma60": 95,
                "high_20d": 110,
                "low_20d": 78,
                "rsi14": 35,
                "volume_ma20": 1000,
            },
            scores={"speculation_score": 40, "growth_score": 45, "quality_score": 50, "risk_score": 65},
        )
        self.assertEqual(decision.action, "SELL")
        self.assertIsNone(decision.entry_price)


if __name__ == "__main__":
    unittest.main()
