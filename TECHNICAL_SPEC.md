# 技術仕様

API: audit(db, sql, policy, out, operation_id) -> report dict。CLI run/demo。
operation_id、copy_id(UUID)、schema_version=sma-report-v1、入力SHA256、SQLite版、user_versionを記録。
処理: パス検査→ポリシー検査→出力先排他作成→Backup API→ID別保存値取得→authorizer付きSQL→読戻し。
integrity_checkとforeign_key_checkを別フィールドで実行する。前者だけでFK保持とは判定しない。
JSONには不一致ID・列・期待値・実測値、DDL、拒否authorizerイベントを保存。BLOBはhex、型も照合。
MIGRATION_FAILED / DATA_LOSS / FOREIGN_KEY_VIOLATION / UNAPPROVED_SCHEMA_CHANGE /
UNAPPROVED_ROW_ADDITION / INTEGRITY_VIOLATION / UNVERIFIABLEを使用。
元DBの変化や検査例外は2、移行失敗や契約違反は1、証拠を得た全契約一致だけ0。

ポリシー例はsamples/policy.json。未知フィールド・JSON重複キー・不正型・未定義変換を拒否。
すべての保存対象表の元列を列マッピングまたは削除許可に含める。行削除許可はない。
期待スキーマはsqlite_schemaのtype:name→SQL全文。内部sqlite_オブジェクトは除外。
SQLite内部schema_versionは移行時に変化するため保持契約にしない。report schema_versionは証拠形式版。
SQLのPRAGMAは禁止（user_version更新も現版では未対応）。通常のmain DDL/DML/SELECTを提供。
ATTACH、DETACH、仮想表、拡張読込、ファイル関数を拒否。tempカタログの内部ALTER処理だけ例外。
拡張を無効化しtrusted_schema=OFF。任意コマンド・URL・外部DBを指定するAPIはない。
解析/authorizerは悪意あるSQLへの完全隔離ではない。信頼済みSQLの小規模試験に限定。

executescriptは部分コミットし得る。異常時も試験コピーは保持、修復やロールバック保証はしない。
未完了トランザクションはpending分をrollbackして検査不能とする。
通常パスとsymlink拒否はTOCTOU攻撃への保証ではない。入力ハードリンクでも元接続はreadonly。
read-only DBのWAL/SHM補助ファイルが必要な場合がある。主DBハッシュだけで全副作用なしと主張しない。
SQLite資料: https://www.sqlite.org/backup.html 、https://www.sqlite.org/pragma.html

## FIX-01: 接続寿命

fixture/default_policy/auditのreadonly sourceとテスト/比較の全接続をcontextlib.closingで囲む。
`with closing(connect(...)) as c, c:`は右側c.__exit__が先にcommit/rollbackを行い、その後closing.__exit__がcloseする。
比較の早期returnやSQL例外にも同じ順序が適用される。auditのtrial接続は既存finally closeを維持。
Backup API完了→readonly sourceのtransaction exit/close→trialの観測→trial close→JSON保存の順序。
接続以外の業務判定・SQL許可範囲・終了コード・既存32ケース期待値は変更しない。
ResourceWarning gateはPython3.13、alwaysフィルタ、tracemalloc、強制GC3回で検証。
警告を抑止せず捕捉した警告を表示し、0件をJSONに記録する。
