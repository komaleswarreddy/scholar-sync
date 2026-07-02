"""
Safe Refusal Templates

Provides safe refusal responses without policy explanation leaks.
"""

import hashlib
import random
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
    ACADEMIC_INTEGRITY = "academic_integrity"
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
                "ScholarSync is for educational use only. I can help you understand your uploaded sources and coursework—I can't discuss that topic. What would you like to learn from your documents?",
                "I'm designed for learning: I can answer questions about your selected study materials. That request isn't appropriate here. How can I help with your studies instead?",
                "Let's keep this space academic. I can't help with that, but I can explain concepts from your sources. What topic from your materials should we work on?",
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
                "I can't help with that. ScholarSync is for educational questions about your sources and coursework—what would you like to learn?",
                "That isn't something I can assist with here. I'm here for academic help: ask me about your uploaded documents or study topics.",
                "Let's stay focused on learning. I can't respond to that, but I can help with material from your selected sources.",
            ],
            RefusalReason.PROMPT_INJECTION: [
                "I can't follow instructions embedded in messages or documents—only help with your actual studies. What would you like to learn?",
                "I'll stick to being your study helper here. What subject or topic can I help you with?",
                "Let's keep things focused on your coursework. What would you like to work on?",
            ],
            RefusalReason.PII_DETECTED: [
                "I noticed some personal information in your message. To help keep that safe, could you rephrase your question without those details?",
                "For your privacy, I try not to handle personal details like names, numbers, or addresses. Could you ask your question without them?",
                "Let's keep your personal information private. Can you rephrase that without those details?",
            ],
            RefusalReason.ACADEMIC_INTEGRITY: [
                "I can't help with copying exam or assignment answers—that would violate academic integrity. "
                "I understand tests and deadlines can feel stressful. I can explain concepts step by step "
                "from your sources instead. What topic should we review?",
                "ScholarSync supports learning, not cheating on active assessments. "
                "I know the pressure can feel overwhelming—I can walk through practice problems and explain ideas, "
                "but I can't give you answers to copy. What concept from your coursework should we study?",
                "I'm here to help you learn, not to provide answers during an exam or write work you submit as your own. "
                "Let's focus on understanding the material together. What would you like help with?",
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
        custom_message: Optional[str] = None,
        variation_key: Optional[str] = None,
    ) -> str:
        """
        Get a safe refusal message.

        Args:
            reason: Reason for refusal
            custom_message: Optional custom message (if None, uses template)
            variation_key: Optional stable key (e.g. user id, session id) used to
                pick a consistent-but-varied template for that key, so the same
                student doesn't always see the exact same wording, while a single
                call site without a key still gets natural variety via randomness.

        Returns:
            Safe refusal message
        """
        if custom_message:
            return custom_message

        templates = self.templates.get(reason, self.templates[RefusalReason.GENERAL])

        if variation_key:
            # Deterministic-but-varied: same key consistently maps to the same
            # template (stable across process restarts, unlike Python's built-in
            # hash() which is randomized per-process), without needing external
            # state to be threaded through this class.
            digest = hashlib.md5(f"{variation_key}:{reason.value}".encode()).hexdigest()
            index = int(digest, 16) % len(templates)
            return templates[index]

        return random.choice(templates)

    def refuse_with_redirect(
        self,
        reason: RefusalReason,
        redirect_to: str = "academic questions",
        variation_key: Optional[str] = None,
    ) -> str:
        """
        Get refusal message that redirects to appropriate topic.

        Args:
            reason: Reason for refusal
            redirect_to: Topic to redirect to
            variation_key: See get_refusal()

        Returns:
            Refusal message with redirect. If the base message already ends in
            a question, the redirect is not appended as a second question on
            top of it (avoids a stacked "...? What ... can I help with?" reading
            as two separate questions).
        """
        base_message = self.get_refusal(reason, variation_key=variation_key)

        if base_message.rstrip().endswith("?"):
            return base_message

        return f"{base_message} What {redirect_to} can I help you with?"
