# Features

## Overview

One page per supported command. These pages cover how to run each feature; the reasoning lives in the
[governance policy](../rules/policy.md).

| Feature | Command | Page |
| --- | --- | --- |
| List approved inventory | `scan_*.py --list` | [Check what is approved and verified](list-approved.md) |
| Scan and verify | `scan_*.py --scope …` | [Scan content and verify integrity](scan.md) |
| Promote a candidate | `promote_*.py` | [Promote reviewed material](promote.md) |
| Reseal a maintainer edit | `reseal_approved.py` | [Reseal an edited approved item](reseal.md) |
| Accept a medium-risk finding | `--accept-risk RULE_ID` | [Accept a medium finding deliberately](accept-risk.md) |
| Enforcement hook | `enforce_claude_policy.py` | [Understand the shell hook](enforcement-hook.md) |
| Share memory privately | `scan_memory.py --root …` | [Share memory across machines](share-memory.md) |

All scripts: Python 3.10+, standard library only, run from any directory (`python3 scripts/<name>.py`). `--help` on any
script prints its flags.
