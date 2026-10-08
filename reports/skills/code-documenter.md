# Candidate assessment: code-documenter

- Status: quarantined; manual review pending
- Decision: do not promote pending line-level review
- Preliminary severity: **high**
- Intake date: 2026-09-06
- Upstream: https://github.com/Jeffallan/claude-skills/tree/882ef55e377dbf9a4dbe496bb41ac6ccd0e555cf/skills/code-documenter
- Upstream commit: `882ef55e377dbf9a4dbe496bb41ac6ccd0e555cf`
- Candidate tree digest: `sha256:3f29c96402e3d6387e366f7e6d75d756635b0d33cdd123c198a8dc7d1fcfcc10`
- Package: nine UTF-8 Markdown files, 50,970 bytes

## Static scan

- Blocking: yes
- `SECRET_ACCESS` — high — `references/documentation-systems.md:39`
- `SECRET_ACCESS` — high — `references/interactive-api-docs.md:76`
- `SECRET_ACCESS` — high — `references/user-guides-tutorials.md:13`
- `PACKAGE_INSTALL` — medium — `references/coverage-reports.md:106`
- `PACKAGE_INSTALL` — medium — `references/documentation-systems.md:221`
- `PACKAGE_INSTALL` — medium — `references/interactive-api-docs.md:468`
- `PACKAGE_INSTALL` — medium — `references/user-guides-tutorials.md:20`
- `PARENT_PATH` — medium — `references/user-guides-tutorials.md:100`

The scanner labels are not yet manual verdicts. Each match and all referenced instructions must be reviewed before any decision.

No risk has been accepted and no promotion has been attempted.
