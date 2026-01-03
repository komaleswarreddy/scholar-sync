"""
Ingestion Service

Handles file upload, text extraction, chunking, embedding generation, and vector indexing.
All operations are tenant-scoped for data isolation.
"""

import uuid
from typing import List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.source import Source, SourceType, SourceStatus
from app.services.vector import VectorService
from app.services.storage import StorageService
from app.services.text_processing import TextProcessor

import pypdf
import io


class IngestionService:
    """
    Service for processing and indexing source documents.
    
    Business Logic:
    1. Upload file to S3 (tenant-scoped path)
    2. Extract text from PDF/text file
    3. Clean and chunk text
    4. Generate embeddings
    5. Index in Pinecone (with tenant namespace)
    6. Save metadata to database
    """
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.vector_service = VectorService(tenant_id)
        self.storage_service = StorageService(tenant_id)
        self.text_processor = TextProcessor()
    
    async def quick_upload(
        self,
        file: UploadFile,
        title: str,
    ) -> dict:
        """
        Quick upload: Save file and create record, return immediately.
        
        Returns:
            Dictionary with source ID, status="processing", and file_content
        """
        source_id = str(uuid.uuid4())
        
        # Read file content once
        file_content = await file.read()
        content_type = file.content_type or ""
        
        # Determine source type
        if content_type == "application/pdf" or (file.filename and file.filename.endswith('.pdf')):
            source_type = SourceType.PDF.value  # Store enum value as string
            file_ext = ".pdf"
        else:
            source_type = SourceType.TEXT.value  # Store enum value as string
            file_ext = ".txt"
        
        # 1. Upload to storage (quick)
        s3_key = f"{self.tenant_id}/{source_id}{file_ext}"
        await self.storage_service.upload_file_bytes(
            file_content=file_content,
            file_path=s3_key,
            content_type=content_type
        )
        
        # 2. Create database record with "processing" status
        source = Source(
            id=uuid.UUID(source_id),
            tenant_id=uuid.UUID(self.tenant_id),
            title=title,
            s3_key=s3_key,
            type=source_type,  # Already a string value
            status=SourceStatus.PROCESSING.value,  # Store enum value as string
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
    
    async def process_file_background(
        self,
        source_id: str,
        content_type: str,
    ):
        """
        Background processing: Extract, chunk, embed, and index.
        Uses batching for speed.
        """
        try:
            # Get source from database to get s3_key
            result = await self.db.execute(
                select(Source).where(Source.id == uuid.UUID(source_id))
            )
            source = result.scalar_one_or_none()
            if not source:
                print(f"⚠️ Source {source_id} not found")
                return
            
            # Download file from storage
            file_content = await self.storage_service.download_file(source.s3_key)
            
            # 2. Extract text
            text = await self._extract_text(file_content, content_type)
            
            # 3. Chunk text
            chunks = self.text_processor.chunk_text(
                text,
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )
            
            # 4. Batch generate embeddings (much faster!)
            print(f"📊 Generating embeddings for {len(chunks)} chunks...")
            embeddings = await self.vector_service.batch_generate_embeddings(
                [chunk for chunk in chunks]
            )
            
            # 5. Batch upsert to Pinecone (much faster!)
            print(f"📊 Upserting {len(chunks)} vectors to Pinecone...")
            vectors_to_upsert = []
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{source_id}_chunk_{i}"
                vectors_to_upsert.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "source_id": source_id,
                        "text": chunk_text,
                        "chunk_index": i,
                    },
                })
            
            # Batch upsert (100 at a time for Pinecone)
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                await self.vector_service.batch_upsert_vectors(batch)
            
            # 6. Update database status
            result = await self.db.execute(
                select(Source).where(Source.id == uuid.UUID(source_id))
            )
            source = result.scalar_one_or_none()
            if source:
                source.status = SourceStatus.INDEXED.value  # Store enum value as string
                source.chunks_count = len(chunks)
                await self.db.commit()
                print(f"✅ Source {source_id} processed successfully: {len(chunks)} chunks")
            else:
                print(f"⚠️ Source {source_id} not found in database")
                
        except Exception as e:
            import traceback
            print(f"❌ Background processing error for {source_id}: {type(e).__name__}: {str(e)}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            # Update status to error
            result = await self.db.execute(
                select(Source).where(Source.id == uuid.UUID(source_id))
            )
            source = result.scalar_one_or_none()
            if source:
                source.status = SourceStatus.ERROR.value  # Store enum value as string
                await self.db.commit()
    
    async def process_upload(
        self,
        file: UploadFile,
        title: str,
    ) -> dict:
        """
        Process uploaded file: extract, chunk, embed, and index.
        
        Args:
            file: Uploaded file object
            title: Display title for source
            
        Returns:
            Dictionary with source ID, status, and chunk count
        """
        source_id = str(uuid.uuid4())
        
        # Read file content once (can only be read once from UploadFile)
        file_content = await file.read()
        content_type = file.content_type
        
        # 1. Upload to S3 (pass bytes directly)
        s3_key = f"{self.tenant_id}/{source_id}.pdf"
        await self.storage_service.upload_file_bytes(
            file_content=file_content,
            file_path=s3_key,
            content_type=content_type
        )
        
        # 2. Extract text (use the already-read content)
        text = await self._extract_text(file_content, content_type)
        
        # 3. Chunk text
        chunks = self.text_processor.chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        
        # 4. Generate embeddings and index in Pinecone
        chunk_ids = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{source_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Generate embedding
            embedding = await self.vector_service.generate_embedding(chunk_text)
            
            # Upsert to Pinecone with tenant namespace
            await self.vector_service.upsert_vector(
                vector_id=chunk_id,
                embedding=embedding,
                metadata={
                    "source_id": source_id,
                    "text": chunk_text,
                    "chunk_index": i,
                },
            )
        
        # 5. Save to database
        # Determine source type from content_type or filename
        if content_type == "application/pdf" or (hasattr(file, 'filename') and file.filename and file.filename.endswith('.pdf')):
            source_type = SourceType.PDF.value  # Store enum value as string
        else:
            source_type = SourceType.TEXT.value  # Store enum value as string
        source = Source(
            id=uuid.UUID(source_id),
            tenant_id=uuid.UUID(self.tenant_id),
            title=title,
            s3_key=s3_key,
            type=source_type,
        )
        self.db.add(source)
        await self.db.commit()
        
        return {
            "id": source_id,
            "title": title,
            "status": "indexed",
            "chunks_count": len(chunks),
            "created_at": source.created_at,
        }
    
    async def _extract_text(self, file_content: bytes, content_type: str) -> str:
        """Extract text from file based on type."""
        if content_type == "application/pdf":
            # Extract from PDF
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif content_type == "text/plain":
            return file_content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {content_type}")
    
    async def list_sources(self) -> List[dict]:
        """List all sources for tenant."""
        result = await self.db.execute(
            select(Source).where(Source.tenant_id == uuid.UUID(self.tenant_id))
        )
        sources = result.scalars().all()
        
        result_list = []
        for s in sources:
            try:
                s3_url = await self.storage_service.get_presigned_url(s.s3_key)
            except Exception as e:
                # If presigned URL generation fails, continue without it
                print(f"Warning: Failed to generate presigned URL for {s.s3_key}: {e}")
                s3_url = None
            
            result_list.append({
                "id": str(s.id),
                "title": s.title,
                "type": s.type if isinstance(s.type, str) else (s.type.value if hasattr(s.type, 'value') else str(s.type)),
                "status": s.status if isinstance(s.status, str) else (s.status.value if hasattr(s.status, 'value') else str(s.status)),
                "chunks_count": s.chunks_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "s3_url": s3_url,
            })
        return result_list
    
    async def delete_source(self, source_id: str):
        """Delete source and all associated vectors."""
        # Delete from database
        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id),
                Source.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        # Delete vectors from Pinecone (filter by source_id in tenant namespace)
        await self.vector_service.delete_vectors_by_source(source_id)
        
        # Delete file from S3
        await self.storage_service.delete_file(source.s3_key)
        
        # Delete from database
        await self.db.delete(source)
        await self.db.commit()

