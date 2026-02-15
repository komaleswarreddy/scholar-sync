"""
Source Service (Ingestion)

Handles source document ingestion, processing, and management.
"""

import uuid
import io
import pypdf
from typing import List, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import settings
from packages.core.database.models.source import Source, SourceType, SourceStatus
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.storage.s3 import S3Storage
from packages.core.rag.chunker import Chunker
from packages.core.processing.context_cache import ContextCache
from packages.core.processing.pdf_preprocessor import PDFPreprocessor

class IngestionService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id  # Validated UUID string from Middleware
        self.user_id = user_id  # Clerk user ID
        
        # Pass tenant_id to downstream services for infrastructure isolation
        self.vector_store = PineconeVectorStore(tenant_id)
        self.storage_service = S3Storage(tenant_id)
        self.chunker = Chunker(use_semantic=getattr(settings, 'USE_SEMANTIC_CHUNKING', True))
        self.context_cache = ContextCache(cache_dir=f"cache/processed_pdfs/{tenant_id}")
        self.pdf_preprocessor = PDFPreprocessor()

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

            # 0. Check cache first (for static PDFs)
            try:
                file_content = await self.storage_service.download_file(source.s3_key)
                if not file_content:
                    raise ValueError("Downloaded file content is empty")
            except Exception as e:
                raise ValueError(f"Failed to download file from storage: {str(e)}")
            
            # Check cache for processed content
            cached_content = self.context_cache.get_cached_content(file_content, tenant_id=self.tenant_id, user_id=self.user_id)
            if cached_content:
                print(f"[CACHE] Using cached content for source {source_id}")
                # Use cached chunks and text
                chunks_with_metadata = cached_content['chunks']
                chunks = [chunk_text for chunk_text, _ in chunks_with_metadata]
                # Update metadata with current source_id and tenant_id
                chunks_with_metadata = [
                    (chunk_text, {**metadata, 'source_id': source_id, 'tenant_id': self.tenant_id})
                    for chunk_text, metadata in chunks_with_metadata
                ]
            else:
                # 1. Extract Text with page metadata (for PDFs)
                try:
                    if content_type == "application/pdf":
                        text, pages = await self._extract_text_with_pages(file_content, pdf_password)
                    else:
                        text = await self._extract_text(file_content, content_type, pdf_password)
                        pages = None
                    
                    if not text or not text.strip():
                        raise ValueError("Extracted text is empty")
                except Exception as e:
                    raise ValueError(f"Failed to extract text: {str(e)}")
                
                # 2. Clean PDF text aggressively (40-70% token reduction)
                if content_type == "application/pdf" and pages:
                    try:
                        # Use PDF preprocessor for aggressive cleaning
                        cleaned_text = self.pdf_preprocessor.clean_text(text, pages)
                        print(f"[PREPROCESSOR] Cleaned PDF text: {len(text)} -> {len(cleaned_text)} chars ({100 * (1 - len(cleaned_text)/len(text)):.1f}% reduction)")
                        text = cleaned_text
                    except Exception as e:
                        print(f"[WARNING] PDF preprocessing failed, using raw text: {e}")
                
                # 3. Chunk Text with semantic chunking and metadata
                try:
                    # Calculate overlap from percentage
                    overlap_percent = getattr(settings, 'CHUNK_OVERLAP_PERCENT', 0.12)
                    overlap = int(settings.CHUNK_SIZE * overlap_percent)
                    
                    # Use chunk_text_with_metadata for page numbers and other metadata
                    chunks_with_metadata = self.chunker.chunk_text_with_metadata(
                        text,
                        chunk_size=settings.CHUNK_SIZE,
                        overlap=overlap,
                        pages=pages,
                        source_id=source_id,
                        tenant_id=self.tenant_id
                    )
                    
                    chunks = [chunk_text for chunk_text, _ in chunks_with_metadata]
                    
                    if not chunks or len(chunks) == 0:
                        raise ValueError("No chunks created from text")
                    
                    print(f"[CHUNKING] Created {len(chunks)} chunks with semantic chunking and {overlap_percent*100:.1f}% overlap")
                except Exception as e:
                    raise ValueError(f"Failed to chunk text: {str(e)}")
                
                # 4. Cache processed content for future use
                try:
                    self.context_cache.cache_content(
                        file_content=file_content,
                        text=text,
                        chunks=chunks_with_metadata,
                        metadata={
                            'source_id': source_id,
                            'chunks_count': len(chunks),
                            'pages_count': len(pages) if pages else None,
                        }
                    )
                    print(f"[CACHE] Cached processed content for source {source_id}")
                except Exception as e:
                    print(f"[WARNING] Failed to cache content: {e}")

            # 5. Generate Embeddings & Upsert
            try:
                embeddings = await self.vector_store.batch_generate_embeddings([c for c in chunks])
                if not embeddings or len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks")
            except Exception as e:
                error_msg = str(e)
                if "api key" in error_msg.lower() or "not configured" in error_msg.lower():
                    raise ValueError(f"Embedding service not configured. Please check your API keys (OpenAI/Pinecone). Original error: {error_msg}")
                raise ValueError(f"Failed to generate embeddings: {error_msg}")
            
            # Build vectors with enriched metadata (page numbers, etc.)
            vectors_to_upsert = []
            for i, ((chunk_text, chunk_metadata), embedding) in enumerate(zip(chunks_with_metadata, embeddings)):
                # Merge chunk metadata with vector metadata
                vector_metadata = {
                    "source_id": source_id,
                    "tenant_id": self.tenant_id,
                    "text": chunk_text,
                    "chunk_index": chunk_metadata.get("chunk_index", i),
                }
                
                # Add page metadata if available
                if "page_start" in chunk_metadata:
                    vector_metadata["page_start"] = chunk_metadata["page_start"]
                    vector_metadata["page_number"] = chunk_metadata["page_start"]  # For backward compatibility
                if "page_end" in chunk_metadata:
                    vector_metadata["page_end"] = chunk_metadata["page_end"]
                
                vectors_to_upsert.append({
                    "id": f"{source_id}_chunk_{i}",
                    "values": embedding,
                    "metadata": vector_metadata
                })

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

            # 6. Calculate and record document costs
            try:
                from packages.core.monitoring.metrics import get_metrics_collector
                from packages.core.guardrails.cost_manager import get_cost_manager
                
                metrics = get_metrics_collector()
                cost_manager = get_cost_manager()
                
                # Calculate embedding cost (using OpenAI embeddings model pricing)
                # OpenAI text-embedding-3-small: $0.02 per 1M tokens
                # Rough estimate: each chunk is ~1000 tokens for embedding
                embedding_tokens = len(chunks) * 1000  # Rough estimate
                embedding_cost = (embedding_tokens / 1_000_000.0) * 0.02
                
                # Processing cost is minimal (just text extraction and chunking)
                processing_cost = 0.001  # Fixed small cost for processing
                
                total_cost = embedding_cost + processing_cost
                
                # Get page count if available (for PDFs)
                pages_count = None
                if content_type == "application/pdf" or source.type == SourceType.PDF.value:
                    try:
                        import pypdf
                        pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                        pages_count = len(pdf_reader.pages)
                    except:
                        pass
                
                # Record document cost
                metrics.record_document_cost(
                    tenant_id=self.tenant_id,
                    source_id=source_id,
                    total_cost=round(total_cost, 6),
                    processing_cost=round(processing_cost, 6),
                    embedding_cost=round(embedding_cost, 6),
                    chunks_count=len(chunks),
                    pages_count=pages_count,
                )
                
                print(f"[INGESTION] Recorded document cost for {source_id}: ${total_cost:.6f} (embedding: ${embedding_cost:.6f}, processing: ${processing_cost:.6f})")
            except Exception as e:
                # Don't fail processing if cost tracking fails
                print(f"[WARNING] Failed to record document cost: {e}")
            
            # 7. Update Database Status
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

    async def _extract_text_with_pages(self, file_content: bytes, pdf_password: str = None) -> Tuple[str, List]:
        """
        Extract text from PDF with page metadata.
        
        Returns:
            Tuple of (full_text, pages) where pages is list of (page_num, page_text) tuples
        """
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                if pdf_password:
                    if not pdf_reader.decrypt(pdf_password):
                        raise ValueError("Incorrect password for PDF. Please provide the correct password.")
                else:
                    if not pdf_reader.decrypt(""):
                        raise ValueError("PDF is password-protected or encrypted. Please provide the password.")
            
            # Extract pages with metadata
            pages = []
            full_text = ""
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages.append((page_num, page_text))
                        full_text += page_text + "\n\n"
                except Exception as page_error:
                    print(f"[WARNING] Failed to extract text from page {page_num}: {str(page_error)}")
                    continue
            
            if not full_text or not full_text.strip():
                raise ValueError("PDF contains no extractable text. This may be a scanned image PDF.")
            
            return full_text.strip(), pages
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
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

