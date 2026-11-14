# Security / 安全条件

Trusted local SQL and synthetic fixtures only. Not a hostile SQL sandbox.
No external targets, production migrations or arbitrary process control.
Keep input and output paths in directories controlled exclusively by the operator.
Reports contain selected values: treat them as potentially sensitive when using private data.
Do not publish real DBs or confidential evidence. Tests use synthetic data only.
Private vulnerability reporting is proposed for the future repository; no active contact is configured.
Copyright confirmed as KenKan964 by FIX-01 instruction. Publisher must configure a private contact before release. CI must pass before public GO.

FIX-01 explicitly closes source and trial connections; no change to trusted-SQL scope or filesystem race limitations. Six GitHub Actions jobs passed on 2026-11-14 (initial import: run #33). Check the latest Actions runs after subsequent changes. Public release remains a separate decision.
