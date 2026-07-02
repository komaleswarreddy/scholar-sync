#!/usr/bin/env python3
"""RETIRED: v2 prompt variants have been removed from the project.

The v2 A/B prompt experiment track was retired. Production serves v1 only
(`default_prompt: v1` in config/models.yaml), and the eval framework now runs
v1-only. This generator previously created `*_v2.j2` templates and registered
them in prompts/registry.yaml + config/models.yaml; running it again would
reintroduce the removed v2 variants, so it is intentionally disabled.

If a future prompt-variant experiment is needed, restore from version control
history rather than re-enabling this stub.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "generate_v2_prompts.py is retired: v2 prompt variants were removed "
        "and this generator is disabled to avoid reintroducing them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
