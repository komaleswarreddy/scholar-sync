"""
Safe Refusal Templates

Provides safe refusal responses without policy explanation leaks.
"""

from typing import Dict, Optional
from enum import Enum


class RefusalReason(Enum):
    """Reasons for refusing a request."""
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    OUT_OF_SCOPE = "out_of_scope"
    ACADEMIC_ONLY = "academic_only"
    SAFETY_VIOLATION = "safety_violation"
    PROMPT_INJECTION = "prompt_injection"
    PII_DETECTED = "pii_detected"
    GENERAL = "general"


class RefusalTemplates:
    """
    Safe refusal templates that don't leak policy details.
    
    Provides child-appropriate refusal messages.
    """
    
    def __init__(self):
        """Initialize refusal templates."""
        self.templates = {
            RefusalReason.INAPPROPRIATE_CONTENT: [
                "I can't help with that topic. Let's focus on your studies instead!",
                "That's not something I can discuss. How about we work on your schoolwork?",
                "I'm here to help with your academic questions. What would you like to learn about?",
            ],
            RefusalReason.OUT_OF_SCOPE: [
                "I'm designed to help with academic questions. Can I help you with your studies instead?",
                "That's outside my area of expertise. What subject are you working on?",
                "I focus on educational content. What would you like to learn about?",
            ],
            RefusalReason.ACADEMIC_ONLY: [
                "I'm here to help with your coursework. What subject are you studying?",
                "Let's focus on your academic questions. What can I help you learn?",
                "I specialize in educational topics. What would you like to know about?",
            ],
            RefusalReason.SAFETY_VIOLATION: [
                "I can't help with that. Let's focus on your studies!",
                "That's not appropriate. How about we work on your schoolwork instead?",
                "I'm here to help with your education. What subject are you working on?",
            ],
            RefusalReason.PROMPT_INJECTION: [
                "I didn't understand that. Can you rephrase your question?",
                "Could you ask that differently? I'm here to help with your studies.",
                "Let's focus on your academic questions. What would you like to learn?",
            ],
            RefusalReason.PII_DETECTED: [
                "I noticed some personal information. For your privacy, please rephrase your question without personal details.",
                "To keep your information safe, please ask your question without including personal details.",
                "Let's keep your information private. Can you rephrase your question?",
            ],
            RefusalReason.GENERAL: [
                "I'm not able to help with that. What academic topic can I assist you with?",
                "That's not something I can help with. Let's focus on your studies!",
                "I'm here to help with your education. What would you like to learn about?",
            ],
        }
    
    def get_refusal(
        self,
        reason: RefusalReason,
        custom_message: Optional[str] = None
    ) -> str:
        """
        Get a safe refusal message.
        
        Args:
            reason: Reason for refusal
            custom_message: Optional custom message (if None, uses template)
            
        Returns:
            Safe refusal message
        """
        if custom_message:
            return custom_message
        
        templates = self.templates.get(reason, self.templates[RefusalReason.GENERAL])
        # Return first template (could randomize in production)
        return templates[0]
    
    def refuse_with_redirect(
        self,
        reason: RefusalReason,
        redirect_to: str = "academic questions"
    ) -> str:
        """
        Get refusal message that redirects to appropriate topic.
        
        Args:
            reason: Reason for refusal
            redirect_to: Topic to redirect to
            
        Returns:
            Refusal message with redirect
        """
        base_message = self.get_refusal(reason)
        return f"{base_message} What {redirect_to} can I help you with?"
