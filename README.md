# SQLite Migration Auditor 0.1.0 candidate

Python 3.11+ standard library; trusted local developer SQL only. Publication HOLD: CI not run.

```sh
python sma.py demo --out new-demo
python sma.py run --db samples/source.sqlite --sql samples/migration.sql --policy samples/policy.json --out new-trial
python -m unittest discover -s tests -v
python compare.py > comparison.json
```

Exit 0: all declared contracts match; 1: violation or migration failure; 2: unverifiable/input/environment failure.
A successful negative-control unittest is not a CLI PASS for defective data.
Source opens mode=ro; Backup API creates trial.sqlite in an exclusive new output directory.
Source is never migrated. Output DB and report remain for review; delete the whole newly created directory manually after review.
Existing destinations and symlink path components are rejected. Do not use concurrently writable or adversarial directories.

Policy version 1 requires complete expected_schema SQL text map, plus tables with key, columns, drop_columns, allow_additions.
Every source column of each declared table must be mapped or explicitly dropped. Keys are non-null text/integer, unique, unchanged.
Mappings have to and transform: identity, upper_ascii, double_integer. No arbitrary expressions or executable policy.
Schema SQL text comparison is exact (formatting differences may be rejected); provide independently reviewed expected DDL.
Unlisted tables have schema protection only, not row preservation. Row additions are a table-level boolean, not content validation.

ATTACH/DETACH, PRAGMA, virtual tables and extension/file functions are denied by authorizer; extensions disabled.
ALTER may inspect/update SQLite temporary catalog internally. SQL may partially commit before failure: trial only, no rollback guarantee.
SQL size 1MB, execution progress deadline 5s, backup deadline 10s; these are cooperative limits, not a sandbox/resource guarantee.
Trusted local SQL only; no protection against hostile same-user filesystem races, arbitrary malicious DBs or all SQLite vulnerabilities.
Source SHA256 is main-file evidence for quiescent fixtures, not WAL-wide immutability. Read-only SQLite may need existing WAL/SHM support.

See TECHNICAL_SPEC.md, REPORT_ja.md, SECURITY.md and OSS_COMPARISON.md. MIT; Copyright (c) 2026 KenKan964, confirmed by FIX-01 instruction.

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
