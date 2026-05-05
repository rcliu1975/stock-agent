import tempfile
import time
import unittest
from pathlib import Path

from scripts.report_browser import list_reports, render_markdown_html, resolve_report_path


class ReportBrowserTests(unittest.TestCase):
    def test_list_reports_sorts_newest_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            older = reports_dir / "older.md"
            newer = reports_dir / "newer.md"
            older.write_text("old", encoding="utf-8")
            time.sleep(0.01)
            newer.write_text("new", encoding="utf-8")
            reports = list_reports(reports_dir)
            self.assertEqual([item.name for item in reports], ["newer.md", "older.md"])

    def test_resolve_report_path_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            (reports_dir / "ok.md").write_text("ok", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                resolve_report_path(reports_dir, "../secret.md")

    def test_resolve_report_path_requires_markdown_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            (reports_dir / "ok.txt").write_text("no", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                resolve_report_path(reports_dir, "ok.txt")

    def test_render_markdown_html_supports_headings_table_and_list(self):
        markdown = """# Title

- item one
- item two

| Name | Score |
| --- | ---: |
| 2330.TW | 88.2 |
"""
        html = render_markdown_html(markdown)
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<ul><li>item one</li><li>item two</li></ul>", html)
        self.assertIn("<table>", html)
        self.assertIn("<th>Name</th>", html)
        self.assertIn("<td>2330.TW</td>", html)


if __name__ == "__main__":
    unittest.main()
