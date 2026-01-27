"""
Source Service (Ingestion)

Handles source document ingestion, processing, and management.
"""

import uuid
import io
import pypdf
from typing import List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import settings
from packages.core.database.models.source import Source, SourceType, SourceStatus
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.storage.s3 import S3Storage
from packages.core.rag.chunker import Chunker

class IngestionService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id  # Validated UUID string from Middleware
        self.user_id = user_id  # Clerk user ID
        
        # Pass tenant_id to downstream services for infrastructure isolation
        self.vector_store = PineconeVectorStore(tenant_id)
        self.storage_service = S3Storage(tenant_id)
        self.chunker = Chunker()

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
        source_id: str = None,
        pdf_password: str = None
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
                    user_id=self.user_id,
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

    async def process_file_background(self, source_id: str, content_type: str, pdf_password: str = None):
        """
        Process uploaded file in background:
        1. Download from storage
        2. Extract text (with optional PDF password for encrypted PDFs)
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
                    Source.tenant_id == tenant_uuid,
                    Source.user_id == self.user_id
                )
            )
            source = result.scalar_one_or_none()
            
            if not source:
                print(f"[ERROR] Source {source_id} not found in database")
                return

            # 1. Extract Text
            try:
                file_content = await self.storage_service.download_file(source.s3_key)
                if not file_content:
                    raise ValueError("Downloaded file content is empty")
            except Exception as e:
                raise ValueError(f"Failed to download file from storage: {str(e)}")

            try:
                text = await self._extract_text(file_content, content_type, pdf_password)
                if not text or not text.strip():
                    raise ValueError("Extracted text is empty")
            except Exception as e:
                raise ValueError(f"Failed to extract text: {str(e)}")
            
            # 2. Chunk Text
            try:
                chunks = self.chunker.chunk_text(
                    text, 
                    settings.CHUNK_SIZE, 
                    settings.CHUNK_OVERLAP
                )
                if not chunks or len(chunks) == 0:
                    raise ValueError("No chunks created from text")
            except Exception as e:
                raise ValueError(f"Failed to chunk text: {str(e)}")

            # 3. Generate Embeddings & Upsert
            try:
                embeddings = await self.vector_store.batch_generate_embeddings([c for c in chunks])
                if not embeddings or len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks")
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
                batch_size = 100
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i+batch_size]
                    await self.vector_store.batch_upsert_vectors(batch)
            except Exception as e:
                error_msg = str(e)
                if "api key" in error_msg.lower() or "not configured" in error_msg.lower():
                    raise ValueError(f"Vector database not configured. Please check your Pinecone API key. Original error: {error_msg}")
                raise ValueError(f"Failed to upsert vectors: {error_msg}")

            # 4. Update Database Status
            try:
                source.status = SourceStatus.INDEXED.value
                source.chunks_count = len(chunks)
                await self.db.commit()
                print(f"[INGESTION] Successfully processed source {source_id}: {len(chunks)} chunks indexed")
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
                    source.error_message = error_msg
                    await self.db.commit()
                    print(f"[ERROR] Updated source {source_id} status to ERROR with message: {error_msg}")
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
                    source.error_message = error_msg
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
                    source.error_message = error_msg
                    await self.db.commit()
                except Exception as db_error:
                    print(f"[ERROR] Failed to update source status: {db_error}")
            
            # Re-raise as ValueError with user-friendly message
            raise ValueError(error_msg)

    async def list_sources(self) -> List[dict]:
        tenant_uuid = uuid.UUID(self.tenant_id)
        result = await self.db.execute(
            select(Source).where(
                Source.tenant_id == tenant_uuid,
                Source.user_id == self.user_id
            )
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
                "error_message": s.error_message,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "s3_url": url,
            })
        return res_list

    async def delete_source(self, source_id: str):
        tenant_uuid = uuid.UUID(self.tenant_id)
        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id), 
                Source.tenant_id == tenant_uuid,
                Source.user_id == self.user_id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise ValueError(f"Source not found or access denied: {source_id}")

        try:
            await self.vector_store.delete_vectors_by_source(source_id)
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

    async def _extract_text(self, file_content: bytes, content_type: str, pdf_password: str = None) -> str:
        if content_type == "application/pdf":
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    if pdf_password:
                        # User provided a password - try to decrypt with it
                        try:
                            if pdf_reader.decrypt(pdf_password):
                                print(f"[INFO] Successfully decrypted password-protected PDF")
                            else:
                                raise ValueError("Incorrect password for PDF. Please provide the correct password.")
                        except ValueError:
                            # Re-raise our custom ValueError
                            raise
                        except Exception as decrypt_error:
                            raise ValueError(f"Failed to decrypt PDF: {str(decrypt_error)}")
                    else:
                        # No password provided - try empty string first
                        # Many PDFs marked as "encrypted" can actually be read without a password
                        # (they have encryption metadata but no user password required)
                        try:
                            if pdf_reader.decrypt(""):
                                print(f"[INFO] PDF marked as encrypted but readable without password")
                            else:
                                # Empty password didn't work - PDF actually requires a password
                                raise ValueError("PDF is password-protected or encrypted. Please provide the password or remove password protection and try again.")
                        except ValueError:
                            # Re-raise our custom ValueError
                            raise
                        except Exception as empty_decrypt_error:
                            # If empty string fails, PDF actually requires a password
                            raise ValueError("PDF is password-protected or encrypted. Please provide the password or remove password protection and try again.")
                
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text() or ""
                        text += page_text
                    except Exception as page_error:
                        # Log page extraction error but continue with other pages
                        print(f"[WARNING] Failed to extract text from page {page_num + 1}: {str(page_error)}")
                        continue
                
                if not text or not text.strip():
                    raise ValueError("PDF contains no extractable text. This may be a scanned image PDF. Please use OCR to extract text first.")
                
                return text
            except ValueError:
                # Re-raise ValueError (our custom errors)
                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                # Handle specific pypdf errors
                if "encrypted" in error_msg.lower() or "password" in error_msg.lower():
                    if pdf_password:
                        raise ValueError("PDF is password-protected. The provided password may be incorrect. Please verify the password and try again.")
                    else:
                        raise ValueError("PDF is password-protected or encrypted. Please provide the password or remove password protection and try again.")
                elif "corrupted" in error_msg.lower() or "invalid" in error_msg.lower() or "read" in error_msg.lower():
                    raise ValueError(f"PDF file appears to be corrupted or invalid: {error_msg}")
                elif error_type in ["PdfReadError", "PdfStreamError", "PdfParseError"]:
                    raise ValueError(f"PDF parsing error: {error_msg}")
                else:
                    raise ValueError(f"Failed to extract text from PDF ({error_type}): {error_msg}")
        elif content_type == "text/plain":
            try:
                return file_content.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError(f"Failed to decode text file. File may not be UTF-8 encoded: {str(e)}")
        else:
            raise ValueError(f"Unsupported file type: {content_type}")

