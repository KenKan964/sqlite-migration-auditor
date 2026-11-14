# FIX-01差分一覧

接続closeを追加した箇所（sma3、compare2、test2＝接続構文として計7箇所）と既存trial finally closeを点検。
正確な差分はFIX01.patch。32ケースの入力SQL・期待終了コード・診断コードは変更なし。
closing contextの追加とwarning gate、公開文書/名義/CI設定を修正。

- sma.py
- compare.py
- tests/test_acceptance.py
- tools/verify_resources.py
- README.md
- README_ja.md
- TECHNICAL_SPEC.md
- SECURITY.md
- LICENSE
- CHANGELOG.md
- REPORT_ja.md
- OSS_COMPARISON.md
- .github/workflows/tests.yml
