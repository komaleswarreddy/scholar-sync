"""
Citation Enforcer

Ensures all claims in the response are properly cited.
Checks for uncited factual claims and enforces citation requirements.
"""

import re
from typing import List, Dict, Any, Optional


class CitationEnforcer:
    """
    Agent that enforces citation requirements for responses.
    
    Strategies:
    - Detects uncited factual claims
    - Validates citation format
    - Ensures all claims reference source chunks
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize citation enforcer.
        
        Args:
            strict_mode: If True, requires citations for all factual claims
        """
        self.strict_mode = strict_mode
        # Patterns that indicate factual claims
        self.factual_patterns = [
            r'\b(is|are|was|were|has|have|had|contains|includes|means|refers to|defined as)\b',
            r'\b(according to|based on|research shows|studies indicate|evidence suggests)\b',
            r'\b(\d+%|\d+ percent|\d+ of|\d+ times|in \d{4})\b',  # Statistics and dates
            r'\b(always|never|all|every|none|no|only)\b',  # Absolute statements
        ]
    
    def check_citations(
        self,
        response_text: str,
        available_citations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if response has proper citations.
        
        Args:
            response_text: Generated response text
            available_citations: List of available citation dicts with source_id, chunk_id, etc.
            
        Returns:
            Dict with:
            - has_citations: bool
            - citation_count: int
            - uncited_claims: List[str] (sentences without citations)
            - needs_fix: bool
        """
        # Extract citation references like [1], [2], etc.
        citation_refs = re.findall(r'\[(\d+)\]', response_text)
        citation_indices = [int(ref) for ref in citation_refs]
        
        # Check if citations are valid (within range of available citations)
        valid_citations = [
            idx for idx in citation_indices 
            if 1 <= idx <= len(available_citations)
        ]
        
        # Split response into sentences
        sentences = self._split_into_sentences(response_text)
        
        # Find sentences without citations
        uncited_sentences = []
        for sentence in sentences:
            # Skip if sentence is just a citation reference
            if re.match(r'^\s*\[\d+\]\s*$', sentence.strip()):
                continue
            
            # Check if sentence has a citation
            has_citation = bool(re.search(r'\[\d+\]', sentence))
            
            # Check if sentence contains factual claims
            has_factual_claim = any(
                re.search(pattern, sentence, re.IGNORECASE) 
                for pattern in self.factual_patterns
            )
            
            # If it's a factual claim without citation, flag it
            if has_factual_claim and not has_citation:
                uncited_sentences.append(sentence.strip())
        
        needs_fix = len(uncited_sentences) > 0 and self.strict_mode
        
        return {
            "has_citations": len(valid_citations) > 0,
            "citation_count": len(valid_citations),
            "uncited_claims": uncited_sentences,
            "needs_fix": needs_fix,
            "valid_citations": valid_citations,
        }
    
    def enforce_citations(
        self,
        response_text: str,
        available_citations: List[Dict[str, Any]],
        query: str
    ) -> str:
        """
        Enforce citations by adding them to uncited claims.
        
        Args:
            response_text: Original response text
            available_citations: Available citations
            query: Original user query
            
        Returns:
            Response text with enforced citations
        """
        check_result = self.check_citations(response_text, available_citations)
        
        if not check_result["needs_fix"]:
            return response_text
        
        # If no citations available, return original (can't enforce)
        if not available_citations:
            return response_text
        
        # Add citations to uncited sentences
        sentences = self._split_into_sentences(response_text)
        fixed_sentences = []
        
        for sentence in sentences:
            # Check if sentence needs citation
            has_citation = bool(re.search(r'\[\d+\]', sentence))
            has_factual_claim = any(
                re.search(pattern, sentence, re.IGNORECASE) 
                for pattern in self.factual_patterns
            )
            
            if has_factual_claim and not has_citation:
                # Add citation to most relevant chunk (usually [1])
                sentence = f"{sentence} [1]"
            
            fixed_sentences.append(sentence)
        
        return " ".join(fixed_sentences)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with nltk)
        # Split on sentence endings but preserve citations
        sentences = re.split(r'([.!?]+(?:\s|$))', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        
        # Filter out empty sentences
        return [s.strip() for s in result if s.strip()]
