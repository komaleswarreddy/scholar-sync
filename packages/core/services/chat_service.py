"""
Chat Service

Handles chat and message persistence operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
import uuid

from packages.core.database.models.chat import Chat, Message


def get_message_count_for_chat(db: AsyncSession, chat_id: uuid.UUID) -> int:
    """Helper to get message count for a chat."""
    result = db.execute(
        select(func.count(Message.id))
        .where(Message.chat_id == chat_id)
    )
    return result.scalar() or 0


class ChatService:
    """Service for managing chats and messages."""

    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        self.user_id = user_id

    async def create_chat(self, title: Optional[str] = None) -> Chat:
        """Create a new chat session."""
        chat = Chat(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            title=title,
        )
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def get_chat(self, chat_id: str) -> Optional[Chat]:
        """Get a chat with all its messages."""
        chat_uuid = uuid.UUID(chat_id) if isinstance(chat_id, str) else chat_id
        try:
            result = await self.db.execute(
                select(Chat)
                .where(Chat.id == chat_uuid)
                .where(Chat.tenant_id == self.tenant_id)
                .where(Chat.user_id == self.user_id)
                .options(selectinload(Chat.messages))
            )
            chat = result.scalar_one_or_none()
            if chat and chat.messages:
                # Sort messages by created_at
                chat.messages.sort(key=lambda m: m.created_at)
            return chat
        except Exception as e:
            import traceback
            error_msg = f"Failed to load chat {chat_id}: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(traceback.format_exc())
            # Check if it's a column error
            error_str = str(e).lower()
            if 'feedback' in error_str or 'column' in error_str or 'does not exist' in error_str or 'no such column' in error_str:
                print(f"[ERROR] =========================================")
                print(f"[ERROR] DATABASE SCHEMA ERROR DETECTED")
                print(f"[ERROR] The 'feedback' column is missing from the messages table.")
                print(f"[ERROR] =========================================")
                print(f"[ERROR] TO FIX: Run the migration script:")
                print(f"[ERROR]   python backend/add_feedback_column.py")
                print(f"[ERROR] Or run this SQL command in your database:")
                print(f"[ERROR]   ALTER TABLE messages ADD COLUMN IF NOT EXISTS feedback VARCHAR;")
                print(f"[ERROR] =========================================")
                raise ValueError(f"Database schema issue: The 'feedback' column is missing from the messages table. Please run: python backend/add_feedback_column.py")
            raise

    async def list_chats(self, limit: int = 50, offset: int = 0) -> List[Chat]:
        """List all chats for the current user."""
        result = await self.db.execute(
            select(Chat)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        chats = list(result.scalars().all())
        return chats

    async def list_chats_with_message_counts(
        self, limit: int = 50, offset: int = 0
    ) -> List[Tuple[Chat, int]]:
        """
        List chats with message counts in a single query (avoids N+1 count queries on the API).
        """
        stmt = (
            select(Chat, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Message.chat_id == Chat.id)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
            .group_by(Chat.id)
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        try:
            result = await self.db.execute(stmt)
            rows = result.all()
            return [(row[0], int(row[1] or 0)) for row in rows]
        except Exception as e:
            # Production-gated fallback for DB pool timeouts (prevents UI hard-fail on incident).
            try:
                from config.settings import settings
                import sqlalchemy

                if getattr(settings, "DB_FAIL_OPEN_ON_POOL_TIMEOUT", True) and isinstance(
                    e, sqlalchemy.exc.TimeoutError
                ):
                    print(
                        "[WARNING] [CHAT] Database pool timeout; returning empty chats list fallback. "
                        "Consider using Supabase transaction pooler (port 6543) or increasing DB pool size."
                    )
                    return []
            except Exception:
                pass
            raise

    async def update_chat_title(self, chat_id: str, title: str) -> Optional[Chat]:
        """Update chat title."""
        chat_uuid = uuid.UUID(chat_id) if isinstance(chat_id, str) else chat_id
        result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_uuid)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
        )
        chat = result.scalar_one_or_none()
        if chat:
            chat.title = title
            await self.db.commit()
            await self.db.refresh(chat)
        return chat

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        citations: Optional[List[dict]] = None
    ) -> Message:
        """Add a message to a chat."""
        chat_uuid = uuid.UUID(chat_id) if isinstance(chat_id, str) else chat_id
        
        # Verify chat exists and belongs to user
        chat_result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_uuid)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
        )
        chat = chat_result.scalar_one_or_none()
        if not chat:
            raise ValueError(f"Chat {chat_id} not found or access denied")

        message = Message(
            chat_id=chat_uuid,
            role=role,
            content=content,
            citations=citations or [],
        )
        self.db.add(message)
        
        # Auto-generate title from first user message if not set
        if not chat.title and role == 'user':
            # Use first 50 characters of first message as title
            chat.title = content[:50] + ('...' if len(content) > 50 else '')
        
        await self.db.commit()
        await self.db.refresh(message)
        # Refresh chat to ensure title is updated in the session
        if not chat.title and role == 'user':
            await self.db.refresh(chat)
        return message

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat and all its messages."""
        chat_uuid = uuid.UUID(chat_id) if isinstance(chat_id, str) else chat_id
        
        try:
            # First verify the chat exists and belongs to the user
            result = await self.db.execute(
                select(Chat)
                .where(Chat.id == chat_uuid)
                .where(Chat.tenant_id == self.tenant_id)
                .where(Chat.user_id == self.user_id)
            )
            chat = result.scalar_one_or_none()
            if not chat:
                return False
            
            delete_messages_stmt = delete(Message).where(Message.chat_id == chat_uuid)
            await self.db.execute(delete_messages_stmt)
            
            delete_chat_stmt = delete(Chat).where(
                and_(
                    Chat.id == chat_uuid,
                    Chat.tenant_id == self.tenant_id,
                    Chat.user_id == self.user_id
                )
            )
            result = await self.db.execute(delete_chat_stmt)
            await self.db.commit()
            
            deleted_count = result.rowcount
            
            # Check if any rows were deleted
            return deleted_count > 0
        except Exception as e:
            await self.db.rollback()
            import traceback
            print(f"[ERROR] Failed to delete chat {chat_id}: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            raise

    async def delete_all_messages(self, chat_id: str) -> int:
        """Delete all messages in a chat. Returns number of messages deleted."""
        chat_uuid = uuid.UUID(chat_id) if isinstance(chat_id, str) else chat_id
        
        # Verify chat exists and belongs to user
        result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_uuid)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise ValueError(f"Chat {chat_id} not found or access denied")
        
        # Delete all messages for this chat
        delete_stmt = delete(Message).where(Message.chat_id == chat_uuid)
        result = await self.db.execute(delete_stmt)
        await self.db.commit()
        
        return result.rowcount

    async def update_message_feedback(
        self,
        message_id: str,
        feedback: Optional[str]
    ) -> Optional[Message]:
        """Update feedback for a message."""
        message_uuid = uuid.UUID(message_id) if isinstance(message_id, str) else message_id
        
        # Verify message exists and belongs to user's chat
        result = await self.db.execute(
            select(Message)
            .join(Chat)
            .where(Message.id == message_uuid)
            .where(Chat.tenant_id == self.tenant_id)
            .where(Chat.user_id == self.user_id)
        )
        message = result.scalar_one_or_none()
        
        if message:
            # Validate feedback value
            if feedback not in [None, 'thumbs_up', 'thumbs_down']:
                raise ValueError("Feedback must be 'thumbs_up', 'thumbs_down', or None")
            
            message.feedback = feedback
            await self.db.commit()
            await self.db.refresh(message)
        
        return message


