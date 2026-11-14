# SQLite Migration Auditor

**Check a SQLite migration against explicit data-preservation rules — on a copy, before touching your source database.**

**v0.1.0 · Experimental · Python 3.11+ · Standard library only · MIT License**

**English** | [日本語](README_ja.md)

## What is it?

SQLite Migration Auditor is a free command-line tool for developers who need to check whether a proposed SQLite schema or data migration preserves the records and values they care about.

A migration can complete without a SQLite integrity error while still deleting a business record, changing a protected value, or introducing an unexpected schema change. This tool checks those expectations rather than relying on database integrity checks alone.

It opens the source database in SQLite read-only mode, creates a separate test database using SQLite's Backup API, runs **trusted local migration SQL on that test copy**, and writes a machine-readable report.

> **Scope:** An experimental, policy-based migration test for controlled local workloads — not a production migration engine, a hostile-SQL sandbox, or a guarantee of zero data loss.

## What it checks

| Check | What the auditor reports |
| --- | --- |
| Business records | Missing records matched by a declared unique business ID |
| Protected values | Changed values in columns configured for preservation or supported transformation |
| Foreign keys | Violations found by SQLite's `foreign_key_check` |
| Database integrity | Findings from SQLite's `integrity_check` |
| Schema contract | Unexpected changes relative to an explicitly reviewed expected schema |
| Unexpected additions | New records where the policy does not permit them |
| Migration execution | SQL failures and cases where the outcome cannot be verified |

The policy specifies which tables and columns matter. The auditor does **not** claim to validate every table's business data automatically.

## Quick start

**Requirements:** Python 3.11 or newer. No third-party Python packages.

Run the built-in synthetic example from the repository root:

```sh
python sma.py demo --out sma-demo-001
```

The command creates a small synthetic source database and migration, runs the audit on a copy, and writes:

```text
sma-demo-001/
  source.sqlite
  migration.sql
  policy.json
  trial/
    trial.sqlite
    report.json
```

Read `sma-demo-001/trial/report.json` or the JSON printed to the terminal. Use a **new output directory** for each run: existing destinations are intentionally rejected.

To audit the checked-in synthetic sample instead:

```sh
python sma.py run \
  --db samples/source.sqlite \
  --sql samples/migration.sql \
  --policy samples/policy.json \
  --out sma-audit-001
```

The command above uses line continuations for POSIX shells. On Windows, enter the same command on one line:

```text
python sma.py run --db samples/source.sqlite --sql samples/migration.sql --policy samples/policy.json --out sma-audit-001
```

These examples are deliberately small and do not use production data.

## Reading a result

The synthetic demo's recorded report includes the following fields (excerpt; IDs and hashes omitted):

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

See [the recorded demo JSON](evidence/demo.stdout.json) for the complete example.

A deliberately defective migration, such as deleting a protected business record from the synthetic `people` table, is expected to return `FAIL` with a `DATA_LOSS` finding. The [acceptance tests](tests/test_acceptance.py) exercise this and other negative cases; the success of a negative-control **test** is not a `PASS` result for the defective migration.

**Exit codes**

| Code | Meaning |
| --- | --- |
| `0` | `PASS`: all declared checks matched |
| `1` | `FAIL`: a migration error or policy violation was detected |
| `2` | `UNVERIFIABLE`: an input, environment, or verification condition prevented a reliable conclusion |

Results are written as JSON; the test database and report are left in the new output directory for inspection.

## How the policy works

See [`samples/policy.json`](samples/policy.json) for a complete, runnable example. Policy version 1 defines:

- `tables`: the tables to check, each with a unique, non-null text/integer `key` and explicit column rules.
- `columns`: source-to-result column mappings with `identity`, `upper_ascii`, or `double_integer` transformations.
- `drop_columns`: source columns explicitly allowed to disappear.
- `allow_additions`: whether a protected table may gain new records (without validating their content).
- `expected_schema`: the complete expected SQLite schema as a `type:name` → SQL-text map.

For each declared table, every original column must be covered by a mapping or approved deletion. The current schema comparison is **exact SQL-text comparison**, so harmless formatting differences may still be reported. Review and update the expected schema deliberately when testing a real migration.

The sample policy is intended only for its synthetic source database; do not assume that it is appropriate for another schema.

## Verification

The project has 32 acceptance scenarios, including intentional data-loss and constraint violations, plus an 80-execution comparison with a standard-library/SQLite baseline. Both approaches matched their defined expected outcomes in the recorded comparison; this **does not demonstrate a superior detection rate**.

GitHub Actions tests **Ubuntu and Windows × Python 3.11, 3.12, and 3.13**. All six jobs passed in [the initial import validation (run #33)](https://github.com/KenKan964/sqlite-migration-auditor/actions/runs/43584941870). For the current branch or later changes, check [the latest Actions runs](https://github.com/KenKan964/sqlite-migration-auditor/actions).

Reproduce checks locally:

```sh
python -m unittest discover -s tests -v
python -X tracemalloc=5 tools/verify_resources.py
python compare.py > comparison.json
```

The resource test checks for unclosed SQLite connections; full details and historical evidence are in [`REPORT_ja.md`](REPORT_ja.md) and [`OSS_COMPARISON.md`](OSS_COMPARISON.md). The file [`evidence/ci_status.json`](evidence/ci_status.json) is an **older, pre-repository CI snapshot**, not the current CI status.

## Safety and limitations

- **Use trusted local SQL only.** SQLite's authorizer restrictions are not a security sandbox against malicious SQL.
- The original DB is opened read-only; the migration runs on the copy. This does not prove safety under live concurrent writes, WAL/SHM activity, hostile filesystem races, or production conditions.
- A script may partially commit to the **test copy** before failing; no atomic rollback of arbitrary migration scripts is promised.
- Existing output paths and symlink path components are rejected, but the tool is not designed for attacker-controlled or shared-writable directories.
- Only declared tables have business-ID/value preservation checks. Composite keys, changing keys, content validation of newly allowed rows, and arbitrary policy transforms are not supported.
- Reports may contain inspected values. **Do not publish private databases or confidential diagnostic JSON.** Remove generated test directories yourself after review.
- Execution and backup deadlines are cooperative limits, not resource isolation or crash-recovery guarantees.

## Documentation

- [日本語 README](README_ja.md)
- [Technical specification / 技術仕様](TECHNICAL_SPEC.md)
- [Security considerations](SECURITY.md)
- [Comparison and measured limits](OSS_COMPARISON.md)
- [Change history](CHANGELOG.md)
- [Acceptance evidence (Japanese)](REPORT_ja.md)
- [MIT License](LICENSE)

**License:** MIT · Copyright © 2026 KenKan964.
