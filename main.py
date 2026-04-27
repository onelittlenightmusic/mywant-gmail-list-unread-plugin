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
import sys
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print(json.dumps({
        "error": "playwright module not found. Install with: pip3 install playwright && playwright install chromium"
    }, ensure_ascii=False))
    sys.exit(1)

CDP_URL = "http://127.0.0.1:9222"
CACHE_FILE = "/tmp/gmail_unread_list.json"
GMAIL_IMPORTANT_URL = "https://mail.google.com/mail/u/0/#imp"


def error_out(message: str) -> None:
    print(json.dumps({"error": message, "count": 0, "emails": []}, ensure_ascii=False))
    sys.exit(1)


def fetch_unread_important(page) -> list[dict]:
    page.goto(GMAIL_IMPORTANT_URL, wait_until="domcontentloaded", timeout=15000)

    try:
        page.wait_for_selector("div[role='main']", timeout=10000)
    except PlaywrightTimeout:
        error_out("Gmailの読み込みがタイムアウトしました。ログイン状態を確認してください。")

    emails = []
    rows = page.query_selector_all("tr.zE")
    if not rows:
        rows = page.query_selector_all("tr[aria-label]")
        rows = [r for r in rows if "未読" in (r.get_attribute("aria-label") or "")]

    for i, row in enumerate(rows, start=1):
        sender_el = row.query_selector("span.yX.xY")
        sender = sender_el.inner_text().strip() if sender_el else "(不明)"

        subject_el = (row.query_selector("span.bqe")
                      or row.query_selector("span[data-thread-id]")
                      or row.query_selector("span.bog"))
        subject = subject_el.inner_text().strip() if subject_el else "(件名なし)"

        date_el = row.query_selector("span.xW.xY") or row.query_selector("td.xW")
        date = date_el.inner_text().strip() if date_el else ""

        thread_id = row.get_attribute("data-thread-id") or ""

        emails.append({
            "no": i,
            "sender": sender,
            "subject": subject,
            "date": date,
            "thread_id": thread_id,
        })

    return emails


def main() -> None:
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            error_out(f"ブラウザに接続できません ({CDP_URL}): {e}")

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        emails = fetch_unread_important(page)

    result = {"count": len(emails), "emails": emails}

    # mark-read スキルが参照するキャッシュを保存
    Path(CACHE_FILE).write_text(json.dumps(emails, ensure_ascii=False, indent=2))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
