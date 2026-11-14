# 0.1.0 / FIX-01 candidate — 2026-11-14

- Explicit SQLite close after transaction exit in production, baseline and test connections.
- Added ResourceWarning gate with forced garbage collection; original 32 cases unchanged.
- Re-ran 32 tests on Python3.12/3.13 and 80 comparison executions on3.13.
- Confirmed MIT copyright: KenKan964.
- Regenerated synthetic samples and SHA256 manifests. Six CI jobs NOT_RUN; public HOLD.
