# Candidate assessment: governance-policy maintainer reseal update

- Status: approved and registry-verified
- Decision: replacement promoted after explicit human approval
- Overall severity: **medium**
- Review date: 2026-09-07
- Approved by: the-goat
- Approved at: 2026-09-07T12:11:04Z
- Source: current approved `governance-policy`, changed for the user-requested maintainer reseal workflow
- Candidate tree digest: `sha256:d0b40ced98f262d711f4e646810d2c9ce3161d9c06444720fb6a805cd1cea288`
- Package: one UTF-8 Markdown file; no scripts, binaries, symlinks, hooks, tool grants, or dependencies

## Static scan

- Blocking: no
- Critical: 0
- High: 0
- Medium: 0
- Low: 0

No scanner risk IDs require acceptance.

## Manual threat review

| Area | Severity | Assessment |
| --- | --- | --- |
| Prompt injection | Low | The update does not relax candidate handling. External and unexplained material remains inert and returns through candidate review. |
| Exfiltration | Low | It adds no instruction to disclose data or access unrelated files or services. |
| Supply chain | Low | The candidate is a focused edit of the digest-verified approved policy skill, not a new external package. |
| Reverse shell | Low | No shell listener, socket, download, or remote-control behavior exists. |
| Credential extraction | Low | No secrets, tokens, credential files, or authentication material are requested. |
| Execution | Low | It names only the repository's scanners, promoters, and new reseal command; it does not execute candidate code. |
| Filesystem | Medium | It deliberately permits maintainers to edit a named approved item in place and permits an agent to do so only after an explicit user request. The item is unusable until review and reseal. |
| Persistence | Medium | Resealing updates the registry digest and history plus a generated wrapper or index. It requires post-scan human approval and records `source: maintainer-edit`. |
| Obfuscation | Low | Plain, readable Markdown with no encoded or hidden content. |
| Network | Low | No network access, remote operation, installation, or publication is authorized. |

## Control review

- External material and upstream changes still require candidate quarantine, scanning, manual review, and explicit promotion approval.
- A digest mismatch is described as “modified and awaiting reseal,” not as proof of hostile content, but agents still cannot use the item.
- `scripts/reseal_approved.py` handles skills, memory, and MCP records through one standard-library implementation and prints every content finding before acceptance.
- `--apply` requires `--maintainer-edit`; agents are expressly forbidden from approving their own edits.
- The target's expected digest/wrapper mismatch is repairable; other integrity failures and critical/high content findings block resealing. Medium content findings require an explicit accepted rule ID.
- Resealing requires an existing registry entry, permits only the target's expected digest/wrapper mismatch, blocks unrelated integrity failures, preserves prior metadata in history, and verifies integrity after writing.
- Successful external promotion consumes the candidate. Dry runs, scanner blocks, and failed promotion attempts retain it.

## Verification

- 55 unit tests pass, including the new skill, memory, and MCP reseal cases.
- The candidate scan reports zero findings.
- Approved skill and memory scans report zero findings.
- The approved MCP scan reports only Playwright's two already-known medium findings: `LOCAL_STDIO_TRANSPORT` and `ARBITRARY_CODE_TOOL`.

Replacement promotion completed through `scripts/promote_skill.py` after the findings were discussed and the user explicitly approved the reseal controls. The approved tree, registry digest, and generated Claude discovery wrapper verify. The successful-promotion candidate copy was removed under the new no-duplication rule.
