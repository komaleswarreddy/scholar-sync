# Phase 5: Security & Student Guardrails

## Overview

Phase 5 implements comprehensive security and safety guardrails for student-facing applications, ensuring child-safe outputs and preventing security vulnerabilities.

## Features Implemented

### 1. ✅ Input + Output Moderation (Safety Filters)

**File**: `packages/core/security/safety_filter.py`

Filters inappropriate content for child-safe outputs:
- **Categories**: Harassment, hate speech, sexual content, violence, self-harm, dangerous, illegal, inappropriate
- **Pattern Matching**: Keyword-based detection with confidence scoring
- **Academic Exceptions**: Allows educational context (e.g., historical violence in literature)
- **Strict Mode**: Configurable strictness level

**Configuration**:
```python
ENABLE_SAFETY_FILTERS: bool = True
SAFETY_STRICT_MODE: bool = True
```

**Integration**:
- Applied to input in `packages/core/services/rag_service.py` before processing
- Applied to output after generation
- Blocks unsafe content and returns safe refusal message

### 2. ✅ Safe Refusal Templates

**File**: `packages/core/security/refusal_templates.py`

Provides safe refusal responses without policy leaks:
- **Child-Appropriate**: Age-appropriate refusal messages
- **No Policy Leaks**: Doesn't reveal system policies or restrictions
- **Redirects**: Redirects to academic topics
- **Multiple Templates**: Different templates for different refusal reasons

**Refusal Reasons**:
- `INAPPROPRIATE_CONTENT`: Inappropriate content detected
- `OUT_OF_SCOPE`: Query outside scope
- `ACADEMIC_ONLY`: Non-academic query
- `SAFETY_VIOLATION`: Safety violation detected
- `PROMPT_INJECTION`: Prompt injection attempt
- `PII_DETECTED`: PII detected in input
- `GENERAL`: General refusal

**Integration**: Used throughout security checks to provide safe error messages

### 3. ✅ Prompt Injection Detection

**File**: `packages/core/security/injection_detector.py`

Detects and blocks prompt injection and jailbreak attempts:
- **Injection Types**: System prompt leak, role playing, ignore instructions, DAN, jailbreak, encoding, multilingual
- **Pattern Matching**: Detects common injection patterns
- **Suspicious Keywords**: Flags suspicious keywords
- **Confidence Scoring**: Calculates detection confidence

**Configuration**:
```python
ENABLE_INJECTION_DETECTION: bool = True
INJECTION_DETECTION_THRESHOLD: float = 0.6
```

**Integration**:
- Applied to input before processing
- Blocks injection attempts and returns safe refusal

### 4. ✅ Syllabus-Locked RAG

**File**: `packages/core/security/restricted_retriever.py`

Restricts RAG to only approved sources:
- **Approved Sources**: Only retrieves from approved source IDs
- **Strict Mode**: Blocks queries if no approved sources available
- **Filter Merging**: Merges with existing filters
- **Source Management**: Add/remove approved sources dynamically

**Configuration**:
```python
ENABLE_SYLLABUS_LOCK: bool = False  # Requires explicit enable
APPROVED_SOURCE_IDS: str = ""  # Comma-separated list
```

**Integration**:
- Wraps base retriever in `packages/core/services/rag_service.py`
- Only retrieves from approved sources when enabled

### 5. ✅ Academic-Only Intent Enforcement

**File**: `packages/core/security/intent_gate.py`

Blocks non-academic queries:
- **Intent Classification**: Classifies queries as academic, personal, entertainment, inappropriate, etc.
- **Academic Patterns**: Detects academic keywords and patterns
- **Non-Academic Detection**: Identifies personal, entertainment, inappropriate queries
- **Strict Mode**: Blocks non-academic queries in strict mode

**Configuration**:
```python
ENABLE_INTENT_GATE: bool = True
INTENT_ACADEMIC_THRESHOLD: float = 0.5
```

**Integration**:
- Applied to input before processing
- Blocks non-academic queries and redirects to academic topics

### 6. ✅ PII Detection & Redaction

**File**: `packages/core/security/pii_detector.py`

Detects and redacts personally identifiable information:
- **PII Types**: Email, phone, SSN, credit card, name, address, date of birth, IP address
- **Pattern Matching**: Regex-based detection
- **Smart Redaction**: Preserves format while masking (e.g., email: `a***@example.com`)
- **Input & Output**: Applied to both input and output

**Configuration**:
```python
ENABLE_PII_DETECTION: bool = True
```

**Integration**:
- Applied to input before processing (redacts and warns)
- Applied to output after generation (redacts PII)

## Settings

All Phase 5 settings in `config/settings.py`:

```python
# Phase 5: Security & Student Guardrails
USE_SECURITY_GUARDRAILS: bool = True  # Master switch
ENABLE_SAFETY_FILTERS: bool = True
ENABLE_REFUSAL_TEMPLATES: bool = True
ENABLE_INJECTION_DETECTION: bool = True
ENABLE_SYLLABUS_LOCK: bool = False  # Requires explicit enable
ENABLE_INTENT_GATE: bool = True
ENABLE_PII_DETECTION: bool = True

# Safety Configuration
SAFETY_STRICT_MODE: bool = True
INJECTION_DETECTION_THRESHOLD: float = 0.6
INTENT_ACADEMIC_THRESHOLD: float = 0.5

# Syllabus Lock
APPROVED_SOURCE_IDS: str = ""  # Comma-separated list
```

## Integration Flow

**Request Flow**:
1. **PII Detection** (Input)
   - Detect PII in user query
   - Redact and warn if found

2. **Prompt Injection Detection**
   - Detect injection attempts
   - Block and return safe refusal

3. **Intent Gate**
   - Classify query intent
   - Block non-academic queries

4. **Safety Filter** (Input)
   - Check for inappropriate content
   - Block unsafe queries

5. **Syllabus Lock** (if enabled)
   - Restrict retrieval to approved sources
   - Block if no approved sources

6. **RAG Processing** (normal flow)
   - Retrieve context
   - Generate answer

7. **Safety Filter** (Output)
   - Check generated output
   - Replace unsafe content with safe message

8. **PII Detection** (Output)
   - Detect PII in output
   - Redact before returning

## Security Layers

1. **Input Validation**: PII detection, injection detection, intent gate, safety filter
2. **Processing Control**: Syllabus lock, restricted retriever
3. **Output Sanitization**: Safety filter, PII redaction

## File Structure

```
packages/core/security/
├── __init__.py                  # Package exports
├── safety_filter.py             # Input/output moderation
├── refusal_templates.py         # Safe refusal responses
├── injection_detector.py        # Prompt injection detection
├── restricted_retriever.py      # Syllabus-locked RAG
├── intent_gate.py               # Academic-only enforcement
└── pii_detector.py              # PII detection and redaction
```

## Usage Examples

### Safety Filter
```python
from packages.core.security import SafetyFilter

filter = SafetyFilter(strict_mode=True)
result = filter.check_input("inappropriate content")
if result["blocked"]:
    # Handle blocked content
    pass
```

### Refusal Templates
```python
from packages.core.security import RefusalTemplates, RefusalReason

templates = RefusalTemplates()
message = templates.get_refusal(RefusalReason.INAPPROPRIATE_CONTENT)
```

### Injection Detection
```python
from packages.core.security import PromptInjectionDetector

detector = PromptInjectionDetector()
result = detector.detect("ignore previous instructions")
if result["is_injection"]:
    # Block injection attempt
    pass
```

### Restricted Retriever
```python
from packages.core.security import RestrictedRetriever

restricted = RestrictedRetriever(
    base_retriever=retriever,
    approved_source_ids=["source1", "source2"],
    strict_mode=True
)
results = await restricted.retrieve(query)
```

### Intent Gate
```python
from packages.core.security import IntentGate

gate = IntentGate(strict_mode=True)
result = gate.check_and_block("personal question")
if result["blocked"]:
    # Block non-academic query
    pass
```

### PII Detector
```python
from packages.core.security import PIIDetector

detector = PIIDetector()
redacted, info = detector.redact("Contact me at john@example.com")
if info["has_pii"]:
    # PII was redacted
    pass
```

## Benefits

1. **Child Safety**: Ensures all outputs are child-safe
2. **Security**: Prevents prompt injection and jailbreak attempts
3. **Privacy**: Protects PII in both input and output
4. **Academic Focus**: Enforces academic-only queries
5. **Content Control**: Syllabus lock restricts to approved sources
6. **Safe Responses**: Provides appropriate refusal messages

## Testing

1. **Safety Filter**:
   - Send inappropriate content → should be blocked
   - Send academic content → should pass

2. **Injection Detection**:
   - Send "ignore previous instructions" → should be blocked
   - Send normal query → should pass

3. **Intent Gate**:
   - Send personal question → should be blocked
   - Send academic question → should pass

4. **PII Detection**:
   - Send query with email → should be redacted
   - Send query with phone → should be redacted

5. **Syllabus Lock**:
   - Query with approved source → should retrieve
   - Query with unapproved source → should be blocked

## Notes

- All security features are optional and can be disabled via settings
- Strict mode provides maximum protection but may be too restrictive
- Syllabus lock requires explicit enable and approved source IDs
- PII detection uses pattern matching (may have false positives/negatives)
- Safety filters use keyword-based detection (can be improved with ML models)
