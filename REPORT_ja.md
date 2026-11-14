# SMA-DEV-001 / FIX-01 是正報告書

2026-11-14。技術是正F01-01〜03を実装・ローカル検証済み。独立再審査へ提出。
F01-04（専用GitHub6環境CI）は未実施。GitHub公開HOLD。

## 修正内容

sma.pyのfixture、default_policy、readonly source接続にclosingを適用。
compare.pyのメモリDB/readonly source、受入テストの合成データ変更用接続にも適用。
内側の既存transaction contextがcommit/rollbackし、その後外側closingがcloseする。
auditのtrial DBの既存finally closeは維持。仕様全体の再設計は行わない。

## 検証結果

|対象|結果|証拠|
|---|---|---|
|旧fixtureの隔離probe|ResourceWarning1件を再現|before_probe.stderr.log|
|Python3.13.5 既存32件|32/32、skip0、ResourceWarning0|resource_gate313.json, tests313.log|
|Python3.12.14 既存32件|32/32、skip0、ResourceWarning0|resource_gate312.json, tests312.log|
|正常デモ（Python3.13）|PASS、終了0、stderr0バイト|demo.stdout.json, demo.stderr.log|
|標準SQLite＋Python比較（Python3.13）|80/80期待一致、stderr0バイト|comparison.json, comparison.stderr.log|

証拠はevidence配下。旧probeは新しく生成した合成DBのみを使い、旧接続警告を検出できることを確認した。
修正版のwarning gateはalways表示設定＋強制GC3回、捕捉した警告を表示し0件以外を失敗とする。
Python3.13実行ではtracemalloc=5も有効。Python3.12には同じ未クローズ検知能力があるとは主張しない。
既存ケースの期待コードは未変更。PASS/0、FAIL/1、UNVERIFIABLE/2の期待一致を32ケースで確認。
元主DB hash不変、symlink/既存先拒否、ATTACH/VACUUM INTO/extension拒否、欠損/FK違反検出を維持。
原本と修正版は別ディレクトリで管理。変更一覧とunified diffはFIX01_CHANGES.mdとFIX01.patch。

## 名義・公開物

依頼書の指定と認証GitHubプロフィールのlogin KenKan964を照合し、
LICENSEをCopyright (c) 2026 KenKan964に変更。個人プロフィールのその他情報は収録しない。
サンプルDBは今回の正常デモで生成し直した匿名合成DB。旧DBや本番業務データは同梱しない。
README日英・仕様・SECURITY・CHANGELOG・本報告を同期。
各公開候補の全ファイルをMANIFEST.sha256で照合。manifest自身は対象外。

## F01-04未実施の理由

専用候補KenKan964/sqlite-migration-auditorのmetadata取得がGitHub API404。
不存在か接続権限不足かは区別できない。ローカルghはGitHubホストに未ログイン。
利用可能な接続APIにはrepository新規作成の機能がない。
この条件では専用private repoで6ジョブを起動・結果取得できず、全件NOT_RUN。
commit SHA・run/job ID・実行URLはnull。設定ファイルの存在を実行成功とは扱わない。
CIにはPython UTF8モード、ResourceWarning gate、demo、比較、証拠uploadを設定済み。
アクセス可能な専用private repoと実行権限が整った時点で6ジョブを実行し、研究部へ証拠を追加する。
既存別製品リポジトリの代用、Public化、Release作成は行っていない。

## 保持する制約

信頼済みローカルSQL専用。authorizerは完全な悪意あるSQL隔離ではない。
主DB SHA不変は停止中の合成データの証拠で、WAL/SHM全体や並行書込みの不変保証ではない。
部分SQL適用、親/OS異常、電源断等の保証は対象外。工数削減・ROI・商用需要は未測定。
技術修正の再審査候補として提出する。最終受入は研究部、公開判定は6環境CI後。
