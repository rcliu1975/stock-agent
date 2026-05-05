#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote


@dataclass(frozen=True)
class ReportEntry:
    name: str
    path: Path
    modified_at: datetime
    size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only browser for stock-agent Markdown reports")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host, default 127.0.0.1")
    parser.add_argument("--port", type=int, default=8787, help="Bind port, default 8787")
    parser.add_argument("--reports-dir", default="reports/daily", help="Directory containing Markdown reports")
    return parser.parse_args()


def list_reports(reports_dir: Path) -> list[ReportEntry]:
    entries: list[ReportEntry] = []
    if not reports_dir.exists():
        return entries
    for path in reports_dir.glob("*.md"):
        stat = path.stat()
        entries.append(
            ReportEntry(
                name=path.name,
                path=path,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size,
            )
        )
    entries.sort(key=lambda item: (item.modified_at, item.name), reverse=True)
    return entries


def resolve_report_path(reports_dir: Path, report_name: str) -> Path:
    safe_name = Path(unquote(report_name)).name
    if safe_name != report_name or not safe_name.endswith(".md"):
        raise FileNotFoundError(report_name)
    path = (reports_dir / safe_name).resolve()
    reports_root = reports_dir.resolve()
    if reports_root not in path.parents:
        raise FileNotFoundError(report_name)
    if not path.is_file():
        raise FileNotFoundError(report_name)
    return path


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_inline_markdown(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def is_table_separator(line: str) -> bool:
    stripped = line.replace(" ", "")
    return bool(stripped) and all(char in "|:-" for char in stripped)


def split_table_cells(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def render_markdown_html(content: str) -> str:
    lines = content.splitlines()
    html_parts: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = " ".join(item.strip() for item in paragraph_lines if item.strip())
        html_parts.append(f"<p>{render_inline_markdown(text)}</p>")
        paragraph_lines.clear()

    def flush_list() -> None:
        if not list_items:
            return
        items_html = "".join(f"<li>{render_inline_markdown(item)}</li>" for item in list_items)
        html_parts.append(f"<ul>{items_html}</ul>")
        list_items.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        header = table_rows[0]
        body = table_rows[1:]
        thead = "".join(f"<th>{render_inline_markdown(cell)}</th>" for cell in header)
        body_rows = []
        for row in body:
            body_rows.append("".join(f"<td>{render_inline_markdown(cell)}</td>" for cell in row))
        tbody = "".join(f"<tr>{row_html}</tr>" for row_html in body_rows)
        html_parts.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>")
        table_rows.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_table()

    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""

        if stripped.startswith("|") and next_line.startswith("|") and is_table_separator(next_line):
            flush_paragraph()
            flush_list()
            header = split_table_cells(stripped)
            table_rows.append(header)
            index += 2
            while index < len(lines):
                row_line = lines[index].strip()
                if not row_line.startswith("|"):
                    break
                table_rows.append(split_table_cells(row_line))
                index += 1
            flush_table()
            continue

        if not stripped:
            flush_all()
            index += 1
            continue

        if stripped.startswith("#"):
            flush_all()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            heading = stripped[level:].strip()
            html_parts.append(f"<h{level}>{render_inline_markdown(heading)}</h{level}>")
            index += 1
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            list_items.append(stripped[2:].strip())
            index += 1
            continue

        paragraph_lines.append(stripped)
        index += 1

    flush_all()
    return "".join(html_parts)


def render_index_html(reports_dir: Path) -> str:
    reports = list_reports(reports_dir)
    latest_html = ""
    if reports:
        latest_html = (
            f'<p><a href="/report/{escape(reports[0].name)}">開啟最新報告</a> '
            f'| <a href="/raw/{escape(reports[0].name)}">原始 Markdown</a></p>'
        )
    rows = []
    for entry in reports:
        rows.append(
            "<tr>"
            f"<td><a href=\"/report/{escape(entry.name)}\">{escape(entry.name)}</a></td>"
            f"<td>{escape(entry.modified_at.strftime('%Y-%m-%d %H:%M:%S'))}</td>"
            f"<td>{escape(format_size(entry.size_bytes))}</td>"
            f"<td><a href=\"/raw/{escape(entry.name)}\">raw</a></td>"
            "</tr>"
        )
    table_html = (
        "<table><thead><tr><th>檔名</th><th>更新時間</th><th>大小</th><th>下載</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        if rows
        else "<p>目前沒有找到任何 `.md` 報告。</p>"
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>stock-agent 報告瀏覽</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f1e8;
      --card: #fffdf9;
      --text: #1e293b;
      --muted: #64748b;
      --border: #d6d3d1;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      font-family: "Noto Sans TC", "PingFang TC", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, #e0f2fe, transparent 24rem),
        linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1rem 4rem;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 1.25rem;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
    }}
    h1 {{
      margin-top: 0;
      font-size: 2rem;
    }}
    p {{
      color: var(--muted);
      line-height: 1.6;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.75rem 0.5rem;
      border-bottom: 1px solid var(--border);
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>stock-agent 報告瀏覽</h1>
      <p>這個頁面只讀顯示 <code>{escape(str(reports_dir))}</code> 內的 Markdown 報告。</p>
      {latest_html}
      {table_html}
    </section>
  </main>
</body>
</html>"""


def render_report_html(report_path: Path) -> str:
    content = report_path.read_text(encoding="utf-8")
    rendered = render_markdown_html(content)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(report_path.name)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f1f5f9;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #cbd5e1;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      font-family: "Iansui", "Noto Sans TC", "PingFang TC", sans-serif;
      background:
        linear-gradient(135deg, #dbeafe 0%, transparent 35%),
        linear-gradient(180deg, #eff6ff 0%, var(--bg) 100%);
      color: var(--text);
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 1.5rem 1rem 3rem;
    }}
    .toolbar {{
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      margin-bottom: 1rem;
      color: var(--muted);
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 1.25rem;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
    }}
    .report {{
      line-height: 1.6;
    }}
    .report h1, .report h2, .report h3 {{
      margin-top: 1.5rem;
      margin-bottom: 0.75rem;
    }}
    .report h1:first-child {{
      margin-top: 0;
    }}
    .report p, .report li {{
      font-size: 1rem;
    }}
    .report code {{
      background: #e2e8f0;
      border-radius: 6px;
      padding: 0.1rem 0.35rem;
      font-family: "JetBrains Mono", "Noto Sans Mono CJK TC", monospace;
      font-size: 0.92em;
    }}
    .report table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0 1.5rem;
      font-size: 0.95rem;
    }}
    .report th, .report td {{
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--border);
      padding: 0.65rem 0.5rem;
    }}
    .report th {{
      background: #f8fafc;
    }}
    .report ul {{
      padding-left: 1.4rem;
    }}
  </style>
</head>
<body>
  <main>
    <div class="toolbar">
      <a href="/">回報告列表</a>
      <a href="/raw/{escape(report_path.name)}">看原始 Markdown</a>
      <span>{escape(report_path.name)}</span>
    </div>
    <section class="card report">
      {rendered}
    </section>
  </main>
</body>
</html>"""


def make_handler(reports_dir: Path) -> type[BaseHTTPRequestHandler]:
    class ReportBrowserHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._dispatch(send_body=True)

        def do_HEAD(self) -> None:  # noqa: N802
            self._dispatch(send_body=False)

        def _dispatch(self, send_body: bool) -> None:
            if self.path in ("/", ""):
                self._send_html(render_index_html(reports_dir), send_body=send_body)
                return
            if self.path == "/healthz":
                self._send_text("ok\n", "text/plain; charset=utf-8", send_body=send_body)
                return
            if self.path.startswith("/report/"):
                report_name = self.path.removeprefix("/report/")
                self._handle_report(report_name, raw=False, send_body=send_body)
                return
            if self.path.startswith("/raw/"):
                report_name = self.path.removeprefix("/raw/")
                self._handle_report(report_name, raw=True, send_body=send_body)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_report(self, report_name: str, raw: bool, send_body: bool) -> None:
            try:
                report_path = resolve_report_path(reports_dir, report_name)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND, "Report not found")
                return
            if raw:
                self._send_text(report_path.read_text(encoding="utf-8"), "text/markdown; charset=utf-8", send_body=send_body)
                return
            self._send_html(render_report_html(report_path), send_body=send_body)

        def _send_html(self, content: str, send_body: bool) -> None:
            encoded = content.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if send_body:
                self.wfile.write(encoded)

        def _send_text(self, content: str, content_type: str, send_body: bool) -> None:
            encoded = content.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if send_body:
                self.wfile.write(encoded)

    return ReportBrowserHandler


def main() -> int:
    args = parse_args()
    reports_dir = Path(args.reports_dir)
    handler = make_handler(reports_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"stock-agent report browser listening on http://{args.host}:{args.port}")
    print(f"reports_dir={reports_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
