import unittest

from src.core.cli import apply_cli_overrides


class CliTests(unittest.TestCase):
    def test_apply_cli_overrides_symbols_and_top_n(self):
        config = {
            "universe": {"source": "db_top_liquidity", "symbols": ["2330.TW", "2317.TW"]},
            "report": {"top_n": 10},
        }
        updated = apply_cli_overrides(config, "2330.TW,2454.TW", 2)
        self.assertEqual(updated["universe"]["symbols"], ["2330.TW", "2454.TW"])
        self.assertEqual(updated["universe"]["source"], "manual")
        self.assertEqual(updated["report"]["top_n"], 2)
        self.assertEqual(config["universe"]["symbols"], ["2330.TW", "2317.TW"])
        self.assertEqual(config["universe"]["source"], "db_top_liquidity")


if __name__ == "__main__":
    unittest.main()
