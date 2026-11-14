# SQLite Migration Auditor

**SQLite移行によるデータ消失や意図しない変更を、元DBを変更せず試験用コピーで検証するCLIツールです。**

**v0.1.0 · 実験版 · Python 3.11以降 · 標準ライブラリのみ · MIT License**

[English](README.md) | **日本語**

## このツールについて

SQLite Migration Auditorは、SQLiteのスキーマ変更やデータ移行を実行する際に、**保存すべき業務レコードと値が移行後も期待どおりであるか**を検証する無料の開発者向けツールです。

SQLiteの整合性検査が正常でも、業務上必要なレコードが削除されたり、保存すべき値が書き換わったり、想定外のスキーマ変更が起こる可能性があります。本ツールはSQLite標準の検査に加えて、開発者が指定した保持ルールと移行結果を照合します。

元DBをSQLiteの読取り専用モードで開き、**SQLite Backup APIで複製した試験用DBにのみ、信頼できるローカル移行SQLを実行**してJSON形式の診断結果を出力します。

> **対象範囲：** 管理されたローカル環境で、明示した保持契約に基づき移行を試験する実験的ツールです。本番環境の移行エンジン、悪意あるSQLの隔離環境、データ消失ゼロの保証ではありません。

## 何を検査できるか

| 検査対象 | 検出する問題 |
| --- | --- |
| 業務レコード | 宣言した一意の業務IDに対応する行の消失 |
| 保護対象の値 | 保持対象列の値や、許可した変換後の値の不一致 |
| 外部キー | SQLiteの`foreign_key_check`による参照整合性違反 |
| DB内部整合性 | SQLiteの`integrity_check`による異常 |
| スキーマ | 事前に指定した期待スキーマと異なる変更 |
| 行の追加 | ポリシーで許可されていないレコードの追加 |
| SQL実行・検証 | 移行SQLの失敗や、信頼できる判定ができない状態 |

業務レコードと値の保持検査は、**ポリシーで指定した表・列に限られます**。DB全体の業務データを無条件に検証するものではありません。

## クイックスタート

**動作環境：** Python 3.11以降。追加のPythonパッケージは必要ありません。

リポジトリのルートディレクトリで、合成データを使ったデモを実行します。

```sh
python sma.py demo --out sma-demo-001
```

このコマンドは合成の元DB・移行SQL・ポリシーを生成し、DBコピーを検査して、次のファイルを作成します。

```text
sma-demo-001/
  source.sqlite
  migration.sql
  policy.json
  trial/
    trial.sqlite
    report.json
```

`sma-demo-001/trial/report.json`を開くと検査結果を確認できます。ターミナルにもJSONが出力されます。**実行するたびに新しい出力先**を指定してください。既存の出力先は意図的に拒否します。

同梱されたサンプルDBを指定して実行する場合：

```sh
python sma.py run --db samples/source.sqlite --sql samples/migration.sql --policy samples/policy.json --out sma-audit-001
```

この例は合成データ専用です。本番DBを使う手順ではありません。

## 診断結果の読み方

実際に記録された正常デモの出力には、次のような項目があります（主要部分を抜粋）。

```json
{
  "status": "PASS",
  "exit_code": 0,
  "findings": [],
  "before_counts": {
    "people": 2,
    "orders": 1
  },
  "integrity_check": ["ok"],
  "foreign_key_check": []
}
```

全項目を含む記録は[正常デモのJSON証拠](evidence/demo.stdout.json)を参照してください。

一方、合成データの`people`表から保護対象の業務レコードを削除するような不正な移行は、`FAIL`と`DATA_LOSS`の診断が期待されます。[受入テスト](tests/test_acceptance.py)では、このような意図的な異常を複数検証しています。**「不正な移行を正しく検出したテストの成功」と「不正な移行のPASS判定」は異なります。**

**終了コードの意味**

| コード | 判定 |
| --- | --- |
| `0` | `PASS`：宣言した検査条件がすべて一致 |
| `1` | `FAIL`：移行SQLの失敗またはポリシー違反を検出 |
| `2` | `UNVERIFIABLE`：入力・実行環境・検査条件の問題で信頼できる判定ができない |

結果はJSONに保存されます。試験用DBとレポートは確認のため残され、自動削除されません。

## 保持ルール（ポリシー）の設定

実行できるポリシー例は[`samples/policy.json`](samples/policy.json)にあります。バージョン1は次を指定します。

- `tables`：検査対象の表。一意でNULLではない文字列・整数の業務`key`を指定します。
- `columns`：元列と移行後の列の対応。変換は`identity`、`upper_ascii`、`double_integer`に対応します。
- `drop_columns`：削除を明示的に許可した元列。
- `allow_additions`：対象表への新規行追加を許可するかどうか（追加された行の内容は検証しません）。
- `expected_schema`：期待する全体スキーマを`type:name`とSQL文字列の対応として指定します。

宣言した表では、**すべての元列について保持・変換または削除許可を指定**する必要があります。現在のスキーマ比較はSQL文字列の厳密比較なので、意味が同じでも書式の差で不一致になる場合があります。期待スキーマは試験目的に合わせて事前に確認してください。

同梱ポリシーは同梱の合成DB用であり、別のDBにそのまま使用することは想定していません。

## テスト・検証状況

32件の受入ケースには、正常な移行に加え、行消失・値改変・参照違反などを意図的に起こす異常ケースが含まれます。また、SQLiteとPython標準機能による比較実験を80回実施し、双方とも定義した期待判定と一致しました。**既存方式より検出性能が優れていると実証した結果ではありません。**

GitHub Actionsでは**Ubuntu・Windows × Python 3.11／3.12／3.13の6環境**を試験します。[初回登録時の検証（実行#33）](https://github.com/KenKan964/sqlite-migration-auditor/actions/runs/43584941870)では6ジョブすべて合格しました。以後の変更を含む最新の結果は[Actions一覧](https://github.com/KenKan964/sqlite-migration-auditor/actions)で確認できます。

ローカル再検証のコマンド：

```sh
python -m unittest discover -s tests -v
python -X tracemalloc=5 tools/verify_resources.py
python compare.py > comparison.json
```

`verify_resources.py`はSQLite接続の未解放警告も確認します。詳細な過去の証拠は[`REPORT_ja.md`](REPORT_ja.md)と[`OSS_COMPARISON.md`](OSS_COMPARISON.md)を参照してください。`evidence/ci_status.json`の`NOT_RUN`は**リポジトリ作成前の履歴記録**であり、現在のCI結果ではありません。

## 安全上の注意と制約

- **信頼できるローカルSQLだけ**を使用してください。SQLite authorizerによる制限は、悪意あるSQLを安全に隔離する仕組みではありません。
- 元DBは読取り専用で開き、移行はコピーへ実行します。ただし、同時書込み、WAL/SHM、悪意あるファイル操作や本番環境での安全性までは保証しません。
- 移行SQLが途中まで試験用DBに確定された後で失敗する場合があります。任意のSQLを常に全体ロールバックできるわけではありません。
- 既存の出力先とシンボリックリンクのあるパス要素を拒否しますが、第三者が書込みできるディレクトリでの運用を前提としていません。
- 業務値の保持判定は宣言した表に限られます。複合キー、キーの変更、許可した追加行の内容検証、任意の変換式には対応しません。
- レポートには検査対象の値が含まれ得ます。**機密DBや診断JSONを公開しないでください。** 試験後のファイルは利用者が確認して削除してください。
- 実行時間・バックアップ時間の制限は協調的な処理制限であり、完全なリソース隔離や障害復旧を保証しません。

## 関連資料

- [English README](README.md)
- [技術仕様書](TECHNICAL_SPEC.md)
- [安全条件・セキュリティ](SECURITY.md)
- [OSS比較と検証の限界](OSS_COMPARISON.md)
- [変更履歴](CHANGELOG.md)
- [受入・是正報告書](REPORT_ja.md)
- [MITライセンス](LICENSE)

**ライセンス：** MIT · Copyright © 2026 KenKan964.
