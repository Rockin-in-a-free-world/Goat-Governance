# Candidate assessment: skill-creator

- Status: quarantined; manual review pending
- Decision: do not promote pending line-level code review
- Preliminary severity: **high**
- Intake date: 2026-09-06
- Upstream: https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/skill-creator
- Upstream commit: `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f`
- Candidate tree digest: `sha256:4557d54c524c67984e4bab23fa436e90196292ae8df4d2093f0ce0e6951bfc1c`
- Package: 18 UTF-8 text files, 224,992 bytes, including Python programs and HTML/JavaScript assets

## Static scan

- Blocking: yes
- `SHELL_EVALUATION` — high — `eval-viewer/generate_review.py:291`
- `SECRET_ACCESS` — high — `scripts/improve_description.py:6`
- `SHELL_EVALUATION` — high — `scripts/improve_description.py:35`
- `SHELL_EVALUATION` — high — `scripts/run_eval.py:85`

The scanner labels are not yet manual verdicts. The subprocess, environment-variable, generated-HTML, and evaluation paths require complete code review before any decision.

No risk has been accepted and no promotion has been attempted.
