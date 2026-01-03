"""
Multi-Tenancy Middleware

Extracts tenant_id from subdomain and injects it into request state.
This ensures all database queries and vector searches are scoped to the correct tenant.

Flow:
1. Extract subdomain from Host header (e.g., "lincoln.scholarsync.com" -> "lincoln")
2. Look up tenant_id from database using subdomain
3. Set tenant_id in request.state for use in route handlers
4. All subsequent operations use this tenant_id for data isolation
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re

from app.core.database import get_db
from app.models.tenant import Tenant


async def tenant_middleware(request: Request, call_next: Callable):
    """
    Middleware to extract and validate tenant from subdomain.
    
    Business Logic:
    - Extracts subdomain from Host header
    - Validates tenant exists in database
    - Injects tenant_id into request.state
    - If tenant not found, returns 404
    
    Security:
    - Prevents access to non-existent tenants
    - Ensures all data operations are tenant-scoped
    """
    # Extract subdomain from Host header
    host = request.headers.get("host", "")
    
    # Pattern: subdomain.scholarsync.com or subdomain.localhost:3000
    subdomain_match = re.match(r"^([a-z0-9-]+)\.", host)
    
    if not subdomain_match:
        # For development, allow localhost without subdomain
        if "localhost" in host or "127.0.0.1" in host:
            # Look up default tenant from database
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(select(Tenant).where(Tenant.subdomain == "default"))
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    # Create default tenant if it doesn't exist
                    tenant = Tenant(subdomain="default", name="Default School")
                    db.add(tenant)
                    await db.commit()
                    await db.refresh(tenant)
                
                request.state.tenant_id = str(tenant.id)
                request.state.subdomain = "default"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid subdomain. Expected format: {subdomain}.scholarsync.com"
            )
    else:
        subdomain = subdomain_match.group(1)
        
        # Look up tenant in database
        # Note: In production, cache tenant lookups for performance
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tenant not found for subdomain: {subdomain}"
                )
            
            # Inject tenant_id into request state
            request.state.tenant_id = str(tenant.id)
            request.state.subdomain = subdomain
    
    response = await call_next(request)
    return response

