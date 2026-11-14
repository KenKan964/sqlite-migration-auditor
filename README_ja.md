# SQLite Migration Auditor 0.1.0 公開候補

Python3.11以降・標準ライブラリのみ。信頼できる開発者のローカルSQL専用。

```sh
python sma.py demo --out new-demo
python sma.py run --db samples/source.sqlite --sql samples/migration.sql --policy samples/policy.json --out new-trial
python -m unittest discover -s tests -v
python compare.py > comparison.json
```

元DBはmode=ro、Backup APIで新規領域へ複製しコピーだけを移行。
終了0は保持契約一致、1は違反・SQL失敗、2は検査不能。負例テストの成功とCLIの合格は別。
コピーDBとreport.jsonは自動削除しない。審査後に生成ディレクトリ全体を手動削除する。
既存出力先とsymlinkを拒否。共有書込み可能領域での実行は対象外。
保持対象表は業務IDと全保存列・許可削除列を指定する。変換はidentity/upper_ascii/double_integerのみ。
expected_schemaは全スキーマのSQL文字列マップ。厳密比較のため書式差でも不一致になる。
対象外表のデータ保持、追加行の内容、複合キー、キー変更は対象外。
元DBハッシュ不変は停止中の合成DBで検証。WAL/SHM全体の不変保証ではない。
本番DBを使った試験は行っていない。6環境CIは設定のみ、公開HOLD。
詳細はTECHNICAL_SPEC.mdとREPORT_ja.mdを参照。

## FIX-01 (2026-11-14)

SQLite connections now close explicitly after the original transaction context exits.
既存のcommit/rollbackの後にcloseを実行。readonlyソース、fixture、policy、比較、受入テストが対象。
Linux Python3.12.14/3.13.5: 32/32 tests each, ResourceWarning=0 after forced GC.
Python3.13 comparison: 80/80 matches; normal demo PASS/0, stderr empty.

```sh
python -X utf8 -W always::ResourceWarning tools/verify_resources.py
python -X utf8 -W always::ResourceWarning sma.py demo --out new-demo-fix01
python -X utf8 -W always::ResourceWarning compare.py > comparison-fix01.json
```

SMA_EVIDENCE selects the directory for per-case evidence. Use Python3.13 to observe SQLite connection ResourceWarning.
For example, PowerShell: `$env:SMA_EVIDENCE='new-evidence'`; POSIX: `SMA_EVIDENCE=new-evidence python ...`.
The gate forces GC three times, prints captured warnings and fails on any ResourceWarning or skipped test.
All six GitHub Actions jobs remain NOT_RUN: dedicated repo inaccessible (API404), local gh unauthenticated.
Public release remains HOLD. See REPORT_ja.md and evidence/ci_status.json.
