"""Studio generation requires sources in exploratory mode."""

import pytest

from packages.core.services.studio_service import StudioService


@pytest.mark.asyncio
async def test_studio_generate_rejects_sources_only_without_ids():
    svc = StudioService(db=None, tenant_id="00000000-0000-0000-0000-000000000001")
    with pytest.raises(ValueError, match="at least one selected source"):
        await svc.generate(
            task_type="quiz",
            source_ids=[],
            context_mode="sources_only",
        )


@pytest.mark.asyncio
async def test_studio_generate_allows_selection_only_without_source_ids():
    svc = StudioService(db=None, tenant_id="00000000-0000-0000-0000-000000000001")
    # Should not raise at source-validation gate; LLM call may fail without API keys.
    try:
        await svc.generate(
            task_type="quiz",
            source_ids=[],
            context_mode="selection_only",
            selection_text="This is a long enough excerpt for selection-only studio mode.",
        )
    except ValueError as exc:
        assert "at least one selected source" not in str(exc)
