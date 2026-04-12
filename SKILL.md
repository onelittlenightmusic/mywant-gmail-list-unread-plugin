---
name: mywant-gmail-list-unread-plugin
description: GmailのImportantラベルにある未読メールをJSON形式で取得する。未読メールの確認・一覧表示・未読数の把握が必要なときに使用する。Playwright経由でChromeのCDPに接続するため、リモートデバッグ有効のChromeが起動している必要がある。
compatibility:
  python: ">=3.10"
  requires:
    - playwright (sync_api)
    - Chrome with remote debugging on port 9222
metadata:
  output-format: json
  json-schema: see "出力JSON形式" section below
---

## 使い方

```bash
python3 "${CLAUDE_SKILL_DIR}/main.py"
```

引数なし。Chromeのリモートデバッグ（ポート9222）が有効になっている必要がある。

## 出力JSON形式

```json
{
  "count": 3,
  "emails": [
    {
      "no": 1,
      "sender": "送信者名",
      "subject": "件名",
      "date": "4月11日",
      "thread_id": "abc123def456"
    }
  ]
}
```

### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `count` | integer | 取得した未読メール数 |
| `emails` | array | 未読メールのリスト |
| `emails[n].no` | integer | メール番号（mark-read で使用） |
| `emails[n].sender` | string | 送信者名 |
| `emails[n].subject` | string | 件名 |
| `emails[n].date` | string | 受信日（例: "4月11日"） |
| `emails[n].thread_id` | string | スレッドID（mark-read での特定に使用） |

### エラー時

```json
{ "error": "ブラウザに接続できません (http://127.0.0.1:9222): ...", "count": 0, "emails": [] }
```
