#!/usr/bin/env python3
"""
Smoke test Studio report + infographic generation with OpenAI.

Notes:
- This bypasses Pinecone context retrieval and uses small dummy context.
- Infographic image generation can cost money; default skips the DALL·E call.

Usage:
  python .\\scripts\\test_studio_report_infographic.py

To enable actual image generation:
  $env:STUDIO_SKIP_IMAGE="0"; python .\\scripts\\test_studio_report_infographic.py
"""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main() -> int:
    load_dotenv()

    # Ensure we never accidentally spend money unless user opts in.
    if os.getenv("STUDIO_SKIP_IMAGE") is None:
        os.environ["STUDIO_SKIP_IMAGE"] = "1"

    from packages.core.services.studio_service import StudioService

    # Create a dummy service; db is not used by these internal calls.
    svc = StudioService(db=None, tenant_id="dev-tenant", user_id="dev-user")  # type: ignore[arg-type]

    context = "Topic: Photosynthesis. Key terms: chlorophyll, light reactions, Calvin cycle."

    print("=" * 70)
    print("Studio smoke test (OpenAI): report + infographic")
    print("=" * 70)

    print("\n[1/2] report")
    rep = await svc._generate_report("report", context, custom_instructions="Keep it concise and clear.")
    assert rep.get("task_type") == "report"
    assert isinstance(rep.get("content"), str) and rep["content"].strip()
    print(f"[OK] report content length: {len(rep['content'])}")

    print("\n[2/2] infographic")
    info = await svc._generate_infographic("infographic", context, custom_instructions="Make it student-friendly.")
    assert info.get("task_type") == "infographic"
    assert isinstance(info.get("content"), str) and info["content"].strip()

    if info.get("image_skipped"):
        assert isinstance(info.get("dalle_prompt"), str) and info["dalle_prompt"].strip()
        print("[OK] infographic prompt generated; image skipped (set STUDIO_SKIP_IMAGE=0 to generate).")
        print(f"[OK] dalle_prompt length: {len(info['dalle_prompt'])}")
    elif info.get("image_url"):
        print("[OK] infographic image generated.")
        print(f"[OK] image_url: {info['image_url']}")
    else:
        # If image generation fails, we still consider prompt generation OK, but flag it.
        print("[WARN] infographic did not return image_url.")
        print(f"       image_error: {info.get('image_error')}")

    print("\n[OK] Studio smoke test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

