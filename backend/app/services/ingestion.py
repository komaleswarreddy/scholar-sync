import uuid
import io
import pypdf
from typing import List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.source import Source, SourceType, SourceStatus
from app.services.vector import VectorService
from app.services.storage import StorageService
from app.services.text_processing import TextProcessor

class IngestionService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id  # Validated UUID string from Middleware
        
        # Pass tenant_id to downstream services for infrastructure isolation
        self.vector_service = VectorService(tenant_id)
        self.storage_service = StorageService(tenant_id)
        self.text_processor = TextProcessor()

    async def quick_upload(self, file: UploadFile, title: str) -> dict:
        """
        Handles the initial file upload to S3 and creates a 'PROCESSING' record in the DB.
        """
        source_id = str(uuid.uuid4())
        file_content = await file.read()
        content_type = file.content_type or ""
        file_ext = ".txt"
        source_type = SourceType.TEXT.value

        # Detect PDF vs Text
        if content_type == "application/pdf" or (file.filename and file.filename.endswith(".pdf")):
            source_type = SourceType.PDF.value
            file_ext = ".pdf"

        # Multi-tenant Storage Path: {tenant_id}/{source_id}.{ext}
        s3_key = f"{self.tenant_id}/{source_id}{file_ext}"
        await self.storage_service.upload_file_bytes(file_content, s3_key, content_type)

        # Create Database Record
        source = Source(
            id=uuid.UUID(source_id),
            tenant_id=self.tenant_id,  # Critical: Tie data to tenant
            title=title,
            s3_key=s3_key,
            type=source_type,
            status=SourceStatus.PROCESSING.value,
            chunks_count=0,
        )
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)

        return {
            "id": source_id,
            "title": title,
            "status": SourceStatus.PROCESSING.value,
            "chunks_count": 0,
            "created_at": source.created_at,
        }

    async def process_file_background(self, source_id: str, content_type: str):
        """
        Background worker that extracts text, chunks it, and upserts to Vector DB.
        Includes a tenant-check to prevent cross-tenant data processing.
        """
        try:
            # Verify the source belongs to the requesting tenant before processing
            result = await self.db.execute(
                select(Source).where(
                    Source.id == uuid.UUID(source_id),
                    Source.tenant_id == self.tenant_id
                )
            )
            source = result.scalar_one_or_none()
            
            if not source:
                print(f"Access Denied or Not Found: Source {source_id} for Tenant {self.tenant_id}")
                return

            # 1. Extract Text
            file_content = await self.storage_service.download_file(source.s3_key)
            text = await self._extract_text(file_content, content_type)
            
            # 2. Chunk Text
            chunks = self.text_processor.chunk_text(
                text, 
                settings.CHUNK_SIZE, 
                settings.CHUNK_OVERLAP
            )

            # 3. Generate Embeddings & Upsert to Vector DB
            # VectorService(tenant_id) ensures the vectors go into the correct namespace
            embeddings = await self.vector_service.batch_generate_embeddings([c for c in chunks])
            
            vectors_to_upsert = [
                {
                    "id": f"{source_id}_chunk_{i}", 
                    "values": e, 
                    "metadata": {
                        "source_id": source_id, 
                        "tenant_id": self.tenant_id,
                        "text": c, 
                        "chunk_index": i
                    }
                }
                for i, (c, e) in enumerate(zip(chunks, embeddings))
            ]

            # Batch upsert (Pinecone/Milvus/etc)
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                await self.vector_service.batch_upsert_vectors(vectors_to_upsert[i:i+batch_size])

            # 4. Update Database Status
            source.status = SourceStatus.INDEXED.value
            source.chunks_count = len(chunks)
            await self.db.commit()
            print(f"Source {source_id} (Tenant: {self.tenant_id}) processed successfully")

        except Exception as e:
            print(f"Background error for {source_id} [Tenant: {self.tenant_id}]: {e}")
            # Ensure we update the status even on failure
            if 'source' in locals() and source:
                source.status = SourceStatus.ERROR.value
                await self.db.commit()

    async def list_sources(self) -> List[dict]:
        """
        Returns all sources belonging to the tenant.
        """
        result = await self.db.execute(
            select(Source).where(Source.tenant_id == self.tenant_id)
        )
        sources = result.scalars().all()
        
        res_list = []
        for s in sources:
            try:
                # Generate a temporary download link
                url = await self.storage_service.get_presigned_url(s.s3_key)
            except Exception:
                url = None
                
            res_list.append({
                "id": str(s.id),
                "title": s.title,
                "type": s.type,
                "status": s.status,
                "chunks_count": s.chunks_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "s3_url": url,
            })
        return res_list

    async def delete_source(self, source_id: str):
        """
        Deletes source from DB, S3, and Vector DB.
        """
        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id), 
                Source.tenant_id == self.tenant_id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise ValueError(f"Source not found or access denied: {source_id}")

        # Clean up external services
        await self.vector_service.delete_vectors_by_source(source_id)
        await self.storage_service.delete_file(source.s3_key)
        
        # Clean up database
        await self.db.delete(source)
        await self.db.commit()

    async def _extract_text(self, file_content: bytes, content_type: str) -> str:
        """
        Internal helper for text extraction.
        """
        if content_type == "application/pdf":
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        elif content_type == "text/plain":
            return file_content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {content_type}")