import os
import tempfile
import unittest
from pathlib import Path

from src.core.env import load_dotenv


class EnvTests(unittest.TestCase):
    def test_load_dotenv_sets_missing_values_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            env_path = root / ".env"
            env_path.write_text("FOO=bar\nBAR=baz\n", encoding="utf-8")

            previous_foo = os.environ.get("FOO")
            previous_bar = os.environ.get("BAR")
            os.environ["BAR"] = "keep"
            try:
                load_dotenv(root)
                self.assertEqual(os.environ.get("FOO"), "bar")
                self.assertEqual(os.environ.get("BAR"), "keep")
            finally:
                if previous_foo is None:
                    os.environ.pop("FOO", None)
                else:
                    os.environ["FOO"] = previous_foo
                if previous_bar is None:
                    os.environ.pop("BAR", None)
                else:
                    os.environ["BAR"] = previous_bar


if __name__ == "__main__":
    unittest.main()
