"""
Studio Feature Service

Handles saving and retrieving generated studio features.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from packages.core.database.models.studio_feature import StudioFeature


class StudioFeatureService:
    """Service for managing studio-generated features."""

    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        self.user_id = user_id

    async def save_feature(
        self,
        *,
        notebook_id: str,
        feature_type: str,
        title: str,
        content: Dict[str, Any],
        source_ids: Optional[List[str]] = None,
    ) -> StudioFeature:
        """Save a generated studio feature."""
        notebook_uuid = uuid.UUID(notebook_id) if isinstance(notebook_id, str) else notebook_id
        feature = StudioFeature(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            notebook_id=notebook_uuid,
            type=feature_type,
            title=title,
            content=content,
            source_ids=source_ids or [],
        )
        self.db.add(feature)
        await self.db.commit()
        await self.db.refresh(feature)
        return feature

    async def get_features(
        self,
        limit: int = 50,
        offset: int = 0,
        feature_type: Optional[str] = None,
        notebook_id: Optional[str] = None,
    ) -> List[StudioFeature]:
        """Get features for the current user, optionally scoped to a notebook."""
        conditions = [
            StudioFeature.tenant_id == self.tenant_id,
            StudioFeature.user_id == self.user_id,
        ]

        if feature_type:
            conditions.append(StudioFeature.type == feature_type)
        if notebook_id:
            notebook_uuid = uuid.UUID(notebook_id) if isinstance(notebook_id, str) else notebook_id
            conditions.append(StudioFeature.notebook_id == notebook_uuid)

        query = (
            select(StudioFeature)
            .where(and_(*conditions))
            .order_by(StudioFeature.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_feature(self, feature_id: str) -> Optional[StudioFeature]:
        """Get a specific feature by ID."""
        feature_uuid = uuid.UUID(feature_id) if isinstance(feature_id, str) else feature_id
        result = await self.db.execute(
            select(StudioFeature).where(
                and_(
                    StudioFeature.id == feature_uuid,
                    StudioFeature.tenant_id == self.tenant_id,
                    StudioFeature.user_id == self.user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_feature(self, feature_id: str) -> bool:
        """Delete a feature by ID."""
        feature = await self.get_feature(feature_id)
        if feature:
            await self.db.delete(feature)
            await self.db.commit()
            return True
        return False
