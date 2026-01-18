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
        try:
            source_id = str(uuid.uuid4())
            
            # Read file content
            try:
                file_content = await file.read()
                if not file_content:
                    raise ValueError("File content is empty after reading")
            except Exception as e:
                raise ValueError(f"Failed to read file content: {str(e)}")
            
            content_type = file.content_type or ""
            filename = file.filename or ""
            return await self.quick_upload_bytes(file_content, filename, content_type, title, source_id)
        except Exception as e:
            # Re-wrap or re-raise errors to be handled by the endpoint
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Ingestion service failure: {str(e)}")

    async def quick_upload_bytes(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str, 
        title: str,
        source_id: str = None
    ) -> dict:
        """
        Handles the initial file upload to S3 and creates a 'PROCESSING' record in the DB.
        Accepts file content as bytes directly.
        """
        try:
            if source_id is None:
                source_id = str(uuid.uuid4())
            
            if not file_content:
                raise ValueError("File content is empty")
            
            file_ext = ".txt"
            source_type = SourceType.TEXT.value

            # Detect PDF vs Text
            if content_type == "application/pdf" or (filename and filename.endswith(".pdf")):
                source_type = SourceType.PDF.value
                file_ext = ".pdf"

            # Multi-tenant Storage Path: {tenant_id}/{source_id}.{ext}
            s3_key = f"{self.tenant_id}/{source_id}{file_ext}"
            
            # Upload to storage
            try:
                await self.storage_service.upload_file_bytes(file_content, s3_key, content_type)
            except Exception as e:
                raise ValueError(f"Storage upload failed: {str(e)}")

            # Create Database Record
            try:
                source = Source(
                    id=uuid.UUID(source_id),
                    tenant_id=uuid.UUID(self.tenant_id),
                    title=title,
                    s3_key=s3_key,
                    type=source_type,
                    status=SourceStatus.PROCESSING.value,
                    chunks_count=0,
                )
                self.db.add(source)
                await self.db.commit()
                await self.db.refresh(source)
            except Exception as e:
                await self.db.rollback()
                raise ValueError(f"Database error: {str(e)}")

            return {
                "id": source_id,
                "title": title,
                "status": SourceStatus.PROCESSING.value,
                "chunks_count": 0,
                "created_at": source.created_at,
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Upload processing failed: {str(e)}")

    async def process_file_background(self, source_id: str, content_type: str):
        """
        Process uploaded file in background:
        1. Download from storage
        2. Extract text
        3. Chunk text
        4. Generate embeddings
        5. Upsert to vector database
        6. Update status to INDEXED
        """
        import traceback
        source = None
        
        try:
            tenant_uuid = uuid.UUID(self.tenant_id)
            result = await self.db.execute(
                select(Source).where(
                    Source.id == uuid.UUID(source_id),
                    Source.tenant_id == tenant_uuid
                )
            )
            source = result.scalar_one_or_none()
            
            if not source:
                print(f"[ERROR] Source {source_id} not found in database")
                return

            print(f"[INGESTION] Starting processing for source {source_id} ({source.title})")

            # 1. Extract Text
            try:
                print(f"[INGESTION] Step 1: Downloading file from storage...")
                file_content = await self.storage_service.download_file(source.s3_key)
                if not file_content:
                    raise ValueError("Downloaded file content is empty")
                print(f"[INGESTION] Step 1: File downloaded, size: {len(file_content)} bytes")
            except Exception as e:
                raise ValueError(f"Failed to download file from storage: {str(e)}")

            try:
                print(f"[INGESTION] Step 2: Extracting text from {content_type}...")
                text = await self._extract_text(file_content, content_type)
                if not text or not text.strip():
                    raise ValueError("Extracted text is empty")
                print(f"[INGESTION] Step 2: Text extracted, length: {len(text)} characters")
            except Exception as e:
                raise ValueError(f"Failed to extract text: {str(e)}")
            
            # 2. Chunk Text
            try:
                print(f"[INGESTION] Step 3: Chunking text...")
                chunks = self.text_processor.chunk_text(
                    text, 
                    settings.CHUNK_SIZE, 
                    settings.CHUNK_OVERLAP
                )
                if not chunks or len(chunks) == 0:
                    raise ValueError("No chunks created from text")
                print(f"[INGESTION] Step 3: Created {len(chunks)} chunks")
            except Exception as e:
                raise ValueError(f"Failed to chunk text: {str(e)}")

            # 3. Generate Embeddings & Upsert
            try:
                print(f"[INGESTION] Step 4: Generating embeddings...")
                embeddings = await self.vector_service.batch_generate_embeddings([c for c in chunks])
                if not embeddings or len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks")
                print(f"[INGESTION] Step 4: Generated {len(embeddings)} embeddings")
            except Exception as e:
                error_msg = str(e)
                if "api key" in error_msg.lower() or "not configured" in error_msg.lower():
                    raise ValueError(f"Embedding service not configured. Please check your API keys (OpenAI/Pinecone). Original error: {error_msg}")
                raise ValueError(f"Failed to generate embeddings: {error_msg}")
            
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

            try:
                print(f"[INGESTION] Step 5: Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
                batch_size = 100
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i+batch_size]
                    await self.vector_service.batch_upsert_vectors(batch)
                    print(f"[INGESTION] Step 5: Upserted batch {i//batch_size + 1}/{(len(vectors_to_upsert) + batch_size - 1)//batch_size}")
                print(f"[INGESTION] Step 5: All vectors upserted successfully")
            except Exception as e:
                error_msg = str(e)
                if "api key" in error_msg.lower() or "not configured" in error_msg.lower():
                    raise ValueError(f"Vector database not configured. Please check your Pinecone API key. Original error: {error_msg}")
                raise ValueError(f"Failed to upsert vectors: {error_msg}")

            # 4. Update Database Status
            try:
                print(f"[INGESTION] Step 6: Updating database status...")
                source.status = SourceStatus.INDEXED.value
                source.chunks_count = len(chunks)
                await self.db.commit()
                print(f"[INGESTION] ✅ Successfully processed source {source_id}: {len(chunks)} chunks indexed")
            except Exception as e:
                await self.db.rollback()
                raise ValueError(f"Failed to update database: {str(e)}")

        except ValueError as e:
            # Re-raise ValueError with clear message
            error_msg = str(e)
            print(f"[ERROR] Processing failed for {source_id}: {error_msg}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            if source:
                try:
                    source.status = SourceStatus.ERROR.value
                    await self.db.commit()
                    print(f"[ERROR] Updated source {source_id} status to ERROR")
                except Exception as db_error:
                    print(f"[ERROR] Failed to update source status: {db_error}")
            raise  # Re-raise to be caught by background task handler
            
        except NameError as e:
            # Handle missing imports (e.g., pinecone, openai not installed)
            error_msg = f"Missing required package: {str(e)}. Please install required dependencies."
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            if source:
                try:
                    source.status = SourceStatus.ERROR.value
                    await self.db.commit()
                except Exception as db_error:
                    print(f"[ERROR] Failed to update source status: {db_error}")
            raise ValueError(error_msg)
            
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error during processing: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            
            if source:
                try:
                    source.status = SourceStatus.ERROR.value
                    await self.db.commit()
                except Exception as db_error:
                    print(f"[ERROR] Failed to update source status: {db_error}")
            
            # Re-raise as ValueError with user-friendly message
            raise ValueError(error_msg)

    async def list_sources(self) -> List[dict]:
        tenant_uuid = uuid.UUID(self.tenant_id)
        result = await self.db.execute(
            select(Source).where(Source.tenant_id == tenant_uuid)
        )
        sources = result.scalars().all()
        
        res_list = []
        for s in sources:
            try:
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
        tenant_uuid = uuid.UUID(self.tenant_id)
        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id), 
                Source.tenant_id == tenant_uuid
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise ValueError(f"Source not found or access denied: {source_id}")

        try:
            await self.vector_service.delete_vectors_by_source(source_id)
        except Exception:
            pass # Non-critical failure

        try:
            await self.storage_service.delete_file(source.s3_key)
        except Exception:
            pass

        try:
            await self.db.delete(source)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise

    async def _extract_text(self, file_content: bytes, content_type: str) -> str:
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