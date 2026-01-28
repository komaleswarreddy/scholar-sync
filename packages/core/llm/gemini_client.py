"""
Gemini LLM Client Implementation

Implements LLMClient interface for Google Gemini models.

Note: Currently using deprecated `google.generativeai` package.
The package is still functional and will continue to work, but Google recommends
migrating to `google.genai` in the future. The deprecation warning is suppressed
to reduce console noise.

TODO: Migrate to `google.genai` package when stable and API-compatible.
Migration guide: https://github.com/google-gemini/deprecated-generative-ai-python
"""

from typing import AsyncGenerator, Optional, Dict, Any, List
import warnings
import sys

# Suppress deprecation warning for google.generativeai at import time
# This catches warnings that occur during the import itself
if not sys.warnoptions:
    warnings.simplefilter('ignore', DeprecationWarning)

# Additional filter for specific google.generativeai warnings
warnings.filterwarnings('ignore', message='.*google.generativeai.*')
warnings.filterwarnings('ignore', message='.*deprecated.*generativeai.*', category=DeprecationWarning)

import google.generativeai as genai
from config.settings import settings
from packages.core.llm._base import LLMClient, LLMResponse, LLMStreamChunk, LLMProvider


class GeminiClient(LLMClient):
    """Gemini implementation of LLMClient."""
    
    def __init__(
        self,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        # Intercept gemini-1.5-flash and replace immediately (not supported in v1beta API)
        if model == "gemini-1.5-flash" or "1.5-flash" in model.lower():
            print(f"[WARNING] [GEMINI] Model 'gemini-1.5-flash' is not supported in v1beta API. Auto-upgrading to 'gemini-2.0-flash-exp'")
            model = "gemini-2.0-flash-exp"
        
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key or self.api_key == "your-gemini-api-key":
            raise ValueError("Gemini API key not configured. Please set GEMINI_API_KEY in .env")
        self._gemini_model = None
        self._configured = False
        # Log the final model name for debugging
        print(f"[DEBUG] [GEMINI] GeminiClient initialized with model: '{self.model}'")
    
    def _configure(self):
        """Lazy configuration of Gemini API."""
        if not self._configured:
            # Configure with API key - use v1 API (stable) instead of v1beta
            # v1beta doesn't support gemini-1.5-flash, so we need v1
            genai.configure(api_key=self.api_key)
            self._configured = True
    
    def _get_safety_settings(self):
        """Get safety settings to reduce blocking while maintaining safety."""
        # Configure safety settings to be less restrictive
        # This helps reduce false positives while still maintaining safety
        return [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
    
    @property
    def gemini_model(self):
        """Lazy initialization of Gemini model."""
        # CRITICAL: Always check if model name changed and reset if needed
        # This handles cases where self.model was changed after initialization
        if self._gemini_model is not None:
            # Check if current model name is the retired one
            if "1.5-flash" in self.model.lower() and "pro" not in self.model.lower():
                print(f"[CRITICAL] [GEMINI] Model name changed to retired model '{self.model}'. Resetting cached model object...")
                self._gemini_model = None  # Force re-initialization
                self.model = "gemini-2.0-flash-exp"  # Upgrade immediately
        
        if self._gemini_model is None:
            self._configure()
            
            # Normalize model name - remove 'models/' prefix if present
            model_name = self.model
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")
            
            # Try to create model with error handling and fallback chain
            # Note: gemini-1.5-flash is not supported in v1beta API
            # Newer models (2.0-flash-exp, 2.5-flash) work with both v1 and v1beta APIs
            model_candidates = []
            
            # Try newer models first, then fallback to older compatible models
            if "1.5-flash" in model_name.lower() or model_name == "gemini-1.5-flash":
                # For 1.5-flash (legacy), try newer models first
                # gemini-1.5-flash is not supported in v1beta API, so prioritize newer models
                model_candidates = [
                    "gemini-2.0-flash-exp",  # Newer experimental model (works with v1)
                    "gemini-2.5-flash",  # Newer stable model (works with v1)
                    "gemini-1.5-pro",  # Pro version (more compatible)
                    "gemini-pro",  # Legacy pro (most compatible)
                    # Note: gemini-1.5-flash removed from fallback as it doesn't work with v1beta
                ]
            elif "2.0" in model_name.lower() or "2.5" in model_name.lower():
                # For newer models, try them first, then fallback
                model_candidates = [
                    model_name,  # Try original name first
                    "gemini-2.0-flash-exp",  # Try experimental (works with v1)
                    "gemini-2.5-flash",  # Try stable newer (works with v1)
                    "gemini-1.5-pro",  # Fallback to pro
                    "gemini-pro",  # Last resort fallback
                ]
            else:
                # For other models, try original first, then fallbacks
                model_candidates = [
                    model_name,  # Try original name first
                    "gemini-2.0-flash-exp",  # Try newer experimental (works with v1)
                    "gemini-2.5-flash",  # Try newer stable (works with v1)
                    "gemini-1.5-pro",  # Fallback to pro
                    "gemini-pro",  # Last resort fallback
                ]
            
            # CRITICAL: Ensure gemini-1.5-flash is NEVER used - replace it before creating model
            if "1.5-flash" in model_name.lower() or model_name == "gemini-1.5-flash":
                print(f"[CRITICAL] [GEMINI] Intercepted retired model 'gemini-1.5-flash' at model creation. Replacing with 'gemini-2.0-flash-exp'")
                model_name = "gemini-2.0-flash-exp"
                self.model = model_name  # Update stored model name
                # Rebuild candidates with new model name
                model_candidates = [
                    "gemini-2.0-flash-exp",
                    "gemini-2.5-flash",
                    "gemini-1.5-pro",
                    "gemini-pro",
                ]
            
            last_error = None
            successful_model = None
            for candidate in model_candidates:
                # Double-check: Never use gemini-1.5-flash (skip it completely)
                if candidate == "gemini-1.5-flash" or ("1.5-flash" in candidate.lower() and "pro" not in candidate.lower()):
                    print(f"[SKIP] [GEMINI] Skipping retired model '{candidate}'")
                    continue
                    
                try:
                    # CRITICAL: Never create GenerativeModel with gemini-1.5-flash
                    # This is the absolute last check before API call
                    if candidate == "gemini-1.5-flash" or ("1.5-flash" in candidate.lower() and "pro" not in candidate.lower()):
                        print(f"[CRITICAL] [GEMINI] BLOCKED: Attempted to create GenerativeModel with retired model '{candidate}'. Skipping.")
                        continue
                    
                    test_model = genai.GenerativeModel(candidate)
                    # Try to actually initialize it (this will fail if model doesn't exist)
                    # We can't test generate_content without an API key, so we just create the model object
                    self._gemini_model = test_model
                    successful_model = candidate
                    print(f"[DEBUG] [GEMINI] Successfully created GenerativeModel with '{candidate}'")
                    if candidate != model_name:
                        print(f"[INFO] [GEMINI] Model '{model_name}' not available, using '{candidate}' instead")
                        # Update self.model to reflect the actual model being used
                        self.model = candidate
                    break
                except Exception as e:
                    error_msg = str(e)
                    error_type = type(e).__name__
                    last_error = e
                    
                    # If it's a 404/NotFound error or v1beta error, try next candidate
                    if ("404" in error_msg or "NotFound" in error_type or 
                        "not found" in error_msg.lower() or 
                        ("v1beta" in error_msg and "not found" in error_msg.lower()) or
                        ("not supported" in error_msg.lower() and "generateContent" in error_msg)):
                        # Log which model failed and continue to next candidate
                        if candidate == model_candidates[0]:  # Only log for first attempt
                            print(f"[INFO] [GEMINI] Model '{candidate}' not available, trying fallback...")
                        continue
                    # For other errors (auth, etc.), re-raise immediately
                    raise
            
            # If all candidates failed, raise with helpful error
            if self._gemini_model is None:
                if last_error:
                    error_msg = str(last_error)
                    raise ValueError(
                        f"Gemini model '{model_name}' not found. "
                        f"Tried: {', '.join(model_candidates)}. "
                        f"Error: {error_msg}. "
                        f"Please check your API key has access to Gemini models and verify the model name is correct."
                    )
                else:
                    raise ValueError(f"Failed to initialize Gemini model '{model_name}'")
        
        return self._gemini_model
    
    def _get_provider(self) -> LLMProvider:
        return LLMProvider.GEMINI
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Gemini."""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature or self.temperature,
        }
        if max_tokens or self.max_tokens:
            generation_config["max_output_tokens"] = max_tokens or self.max_tokens
        
        # Merge with any additional kwargs
        generation_config.update(kwargs)
        
        # FINAL SAFEGUARD: Check model name before API call
        if "1.5-flash" in self.model.lower() and "pro" not in self.model.lower():
            print(f"[CRITICAL] [GEMINI] generate: Detected retired model '{self.model}'. Forcing reset...")
            self._gemini_model = None  # Force re-initialization
            self.model = "gemini-2.0-flash-exp"
            # Re-initialize with new model
            _ = self.gemini_model
        
        # Get model object and check one more time
        # ALWAYS reset if we detect the retired model - don't trust cached objects
        if "1.5-flash" in self.model.lower() and "pro" not in self.model.lower():
            print(f"[CRITICAL] [GEMINI] generate: Final check - model is '{self.model}'. Forcing complete reset...")
            self._gemini_model = None
            self.model = "gemini-2.0-flash-exp"
        
        model_obj = self.gemini_model
        print(f"[DEBUG] [GEMINI] generate: Using model object with self.model='{self.model}'")
        
        try:
            # Add safety settings to reduce blocking
            safety_settings = self._get_safety_settings()
            response = model_obj.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Handle 404 NotFound errors - model not found for API version (especially v1beta)
            if ("404" in error_msg or "NotFound" in error_type or "not found" in error_msg.lower() or 
                ("v1beta" in error_msg and "not found" in error_msg.lower())):
                # Try to recreate model with fallback and retry
                print(f"[WARNING] [GEMINI] Model '{self.model}' failed with 404/v1beta error, attempting fallback...")
                self._gemini_model = None  # Reset model
                # Force fallback by updating model name if it's the problematic one
                original_model = self.model
                if "1.5-flash" in original_model.lower():
                    self.model = "gemini-2.0-flash-exp"  # Upgrade to newer model
                try:
                    # Force re-initialization with fallback
                    model = self.gemini_model
                    response = model.generate_content(
                        full_prompt,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    print(f"[INFO] [GEMINI] Successfully using fallback model '{self.model}'")
                except Exception as retry_error:
                    raise ValueError(f"Gemini model {original_model} not available. Tried fallback to {self.model} but still failed. The model may not be supported in your API plan or region. Error: {str(retry_error)}")
            else:
                # Re-raise other errors
                raise
        
        # Handle response text - check multiple ways to get content
        content = ""
        finish_reason = None
        
        # Try to get text from response
        if hasattr(response, 'text') and response.text:
            content = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            # Check candidates for text
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts'):
                    # Extract text from parts
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    content = "".join(text_parts)
                elif hasattr(candidate.content, 'text'):
                    content = candidate.content.text
            
            # Get finish reason from candidate
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
            elif hasattr(candidate, 'finishReason'):
                finish_reason = candidate.finishReason
        
        # Check if response was blocked
        if finish_reason in ['SAFETY', 'RECITATION', 'OTHER'] or (hasattr(response, 'prompt_feedback') and response.prompt_feedback):
            # Check prompt feedback for blocking
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                if hasattr(feedback, 'block_reason') and feedback.block_reason:
                    raise ValueError(f"Prompt was blocked by safety filters. Reason: {feedback.block_reason}")
        
        # If no content and finish_reason indicates blocking
        if not content and finish_reason in ['SAFETY', 'RECITATION']:
            raise ValueError(f"Response was blocked by safety filters. Finish reason: {finish_reason}")
        
        # Extract usage info if available
        usage = None
        if hasattr(response, 'usage_metadata'):
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', None),
                "completion_tokens": getattr(response.usage_metadata, 'completion_token_count', None),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', None),
            }
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider.value,
            usage=usage,
            metadata={"finish_reason": finish_reason or getattr(response, 'finish_reason', None)}
        )
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream responses from Gemini."""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature or self.temperature,
        }
        if max_tokens or self.max_tokens:
            generation_config["max_output_tokens"] = max_tokens or self.max_tokens
        
        generation_config.update(kwargs)
        
        # FINAL SAFEGUARD: Check model name before API call
        if "1.5-flash" in self.model.lower() and "pro" not in self.model.lower():
            print(f"[CRITICAL] [GEMINI] Detected retired model '{self.model}' before stream API call. Resetting and upgrading...")
            self._gemini_model = None  # Force re-initialization
            self.model = "gemini-2.0-flash-exp"
        
        # Ensure model is initialized (this will trigger fallback if needed)
        # CRITICAL: Always reset model if self.model contains 1.5-flash - don't trust any cached objects
        if "1.5-flash" in self.model.lower() and "pro" not in self.model.lower():
            print(f"[CRITICAL] [GEMINI] stream_generate: Final check - model is '{self.model}'. Forcing complete reset...")
            self._gemini_model = None
            self.model = "gemini-2.0-flash-exp"
        
        model = self.gemini_model
        print(f"[DEBUG] [GEMINI] stream_generate: Using model object with self.model='{self.model}'")
        
        try:
            # Add safety settings to reduce blocking
            safety_settings = self._get_safety_settings()
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Handle 404 NotFound errors - model not found for API version
            if "404" in error_msg or "NotFound" in error_type or "not found" in error_msg.lower() or ("v1beta" in error_msg and "not found" in error_msg.lower()):
                # Try to recreate model with fallback and retry
                print(f"[WARNING] [GEMINI] Model '{self.model}' failed with 404, attempting fallback...")
                # Reset the model to trigger fallback logic
                self._gemini_model = None
                # Force fallback by temporarily changing model name
                original_model = self.model
                if "1.5-flash" in original_model.lower():
                    # gemini-1.5-flash doesn't work with v1beta, use newer models
                    self.model = "gemini-2.0-flash-exp"  # Try newer first
                elif "2.0" in original_model.lower() or "2.5" in original_model.lower():
                    # Already using newer model, try alternative newer model
                    if "2.0" in original_model.lower():
                        self.model = "gemini-2.5-flash"  # Try stable version
                    else:
                        self.model = "gemini-2.0-flash-exp"  # Try experimental
                model = self.gemini_model
                # Use the same safety settings
                safety_settings = self._get_safety_settings()
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                    stream=True
                )
                print(f"[INFO] [GEMINI] Successfully using fallback model '{self.model}'")
            else:
                # Re-raise other errors
                raise
        
        chunks_yielded = 0
        for chunk in response:
            # Extract text from chunk - check multiple ways
            chunk_text = ""
            chunk_finish_reason = None
            
            # Try to get text from chunk
            if hasattr(chunk, 'text') and chunk.text:
                chunk_text = chunk.text
            elif hasattr(chunk, 'candidates') and chunk.candidates:
                # Check candidates for text
                candidate = chunk.candidates[0] if chunk.candidates else None
                if candidate:
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts'):
                            # Extract text from parts
                            text_parts = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                            chunk_text = "".join(text_parts)
                        elif hasattr(candidate.content, 'text'):
                            chunk_text = candidate.content.text
                    
                    # Get finish reason from candidate
                    if hasattr(candidate, 'finish_reason'):
                        chunk_finish_reason = candidate.finish_reason
                    elif hasattr(candidate, 'finishReason'):
                        chunk_finish_reason = candidate.finishReason
            
            # Check if chunk was blocked
            if chunk_finish_reason in ['SAFETY', 'RECITATION', 'OTHER']:
                print(f"[WARNING] [GEMINI] Stream blocked. Finish reason: {chunk_finish_reason}")
                yield LLMStreamChunk(
                    content="",
                    done=True,
                    metadata={"finish_reason": chunk_finish_reason, "blocked": True}
                )
                return
            
            # Yield chunk if it has text (non-empty after stripping whitespace)
            if chunk_text and chunk_text.strip():
                chunks_yielded += 1
                yield LLMStreamChunk(
                    content=chunk_text,
                    done=False,
                    metadata={"finish_reason": chunk_finish_reason}
                )
        
        # Log if no chunks were yielded
        if chunks_yielded == 0:
            print(f"[WARNING] [GEMINI] Stream completed but no text chunks were yielded. This may indicate the model was blocked or returned empty content.")
        
        yield LLMStreamChunk(content="", done=True)
    
    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> List[LLMResponse]:
        """Generate responses for multiple prompts."""
        # Gemini doesn't natively support batch, so sequential
        responses = []
        for prompt in prompts:
            response = await self.generate(prompt, system_prompt, **kwargs)
            responses.append(response)
        return responses


