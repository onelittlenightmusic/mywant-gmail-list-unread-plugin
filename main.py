#!/usr/bin/env python3
"""
list-unread-gmail: GmailのImportantラベルにある未読メールをJSONで出力する。
結果を /tmp/gmail_unread_list.json に保存し、mark-read から参照できるようにする。

出力形式 (JSON):
{
  "count": 3,
  "emails": [
    {"no": 1, "sender": "送信者名", "subject": "件名", "date": "4月11日", "thread_id": "..."}
  ]
}
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

CACHE_FILE = "/tmp/gmail_unread_list.json"
GMAIL_IMPORTANT_URL = "https://mail.google.com/mail/u/0/#imp"
MYWANT_API = os.environ.get("MYWANT_URL", "http://localhost:8080")


def browser_run(url, steps, keep_open=False, background=True, timeout_ms=90000):
    """Runs steps (a @puppeteer/replay UserFlow's Step[] JSON, plus our
    read/readAll/loop/etc. customStep extensions) against url via the mywant
    browser extension — the CDP-free replacement for
    playwright.chromium.connect_over_cdp. See engine/server/handlers_web_wants.go's
    browserRun and mcp/playwright-app/webext-src/browser-run-interpreter.ts.
    background=True (default) opens the tab without stealing focus."""
    payload = json.dumps({
        "url": url, "steps": steps, "keep_open": keep_open,
        "background": background, "timeout_ms": timeout_ms,
    }).encode()
    req = urllib.request.Request(
        f"{MYWANT_API}/api/v1/web-wants/browser-run",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=(timeout_ms / 1000) + 10) as r:
        data = json.loads(r.read())
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result", {})


def report_progress(percentage, message=""):
    print(json.dumps({"_progress": percentage, "_message": message}, ensure_ascii=False), flush=True)


def error_out(message: str) -> None:
    print(json.dumps({"error": message, "count": 0, "emails": []}, ensure_ascii=False), flush=True)
    sys.exit(1)


def fetch_unread_important() -> list[dict]:
    # クラス名は実際のGmail DOM（2026年7月時点）で確認済み: 送信者名は
    # span.zF の name 属性、件名は span.bqe のテキスト、日時は td.xW、
    # thread_idは行(tr)ではなく件名span自身のdata-thread-id属性にある。
    row_fields = {
        "sender": {"selector": "span.zF", "extract": "attr", "attr": "name"},
        "subject": {"selector": "span.bqe, span[data-thread-id], span.bog", "extract": "text"},
        "date": {"selector": "td.xW", "extract": "text"},
        "thread_id": {"selector": "span.bqe, span[data-thread-id]", "extract": "attr", "attr": "data-thread-id"},
    }
    result = browser_run(GMAIL_IMPORTANT_URL, [
        {"type": "waitForElement", "selectors": [["div[role='main']"]], "timeout": 10000},
        # tr.zE が0件なら tr[aria-label*='未読'] にフォールバック（Gmailの表示バリエーション対策）
        {"type": "customStep", "name": "if", "parameters": {
            "condition": {"selector_gone": "tr.zE"},
            "then": [
                {"type": "customStep", "name": "readAll", "parameters": {
                    "selector": "tr[aria-label*='未読']", "as": "rows", "fields": row_fields,
                }},
            ],
            "else": [
                {"type": "customStep", "name": "readAll", "parameters": {
                    "selector": "tr.zE", "as": "rows", "fields": row_fields,
                }},
            ],
        }},
    ], timeout_ms=75000)

    rows = result.get("rows") or []
    emails = []
    for i, row in enumerate(rows, start=1):
        emails.append({
            "no": i,
            "sender": (row.get("sender") or "").strip() or "(不明)",
            "subject": (row.get("subject") or "").strip() or "(件名なし)",
            "date": (row.get("date") or "").strip(),
            "thread_id": row.get("thread_id") or "",
        })
    return emails


def main() -> None:
    report_progress(20, "Navigating to Gmail")
    try:
        emails = fetch_unread_important()
    except Exception as e:
        error_out(f"Gmailの読み込みに失敗しました。ログイン状態を確認してください: {e}")

    report_progress(90, f"Found {len(emails)} unread emails")
    result = {"count": len(emails), "emails": emails}

    # mark-read スキルが参照するキャッシュを保存
    Path(CACHE_FILE).write_text(json.dumps(emails, ensure_ascii=False, indent=2))

    report_progress(100, "Done")
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
