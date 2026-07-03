# ScholarSync — Interaction Intelligence Layer (IIL) & Rich Feedback System

## Developer Specification Document

**Version**: 1.0  
**Status**: Ready for implementation  
**Parent spec**: ScholarSync Source of Truth V2.1  
**Scope**: New capability layer to be built **before** the platform is handed to initial test users  
**Author**: Product  
**Date**: 2026-06-28

---

## 0. How to read this document

This spec defines two tightly coupled systems that sit on top of the existing ScholarSync V1 platform:

1. **Interaction Intelligence Layer (IIL)** — a three-part system that captures user interactions, curates expert-validated knowledge, and uses expert patterns to enrich responses for all users.
2. **Rich Feedback System** — a tiered, explicit feedback mechanism that feeds signals into the IIL.

Both systems are designed for the **live user testing phase**, where handpicked divergent users (students, teachers, tutors, subject matter experts) use the platform. The goal: every expert interaction makes the platform smarter for every subsequent user.

**Relationship to existing spec**: This document extends ScholarSync V1, specifically:
- Extends FR-CHAT-5 (feedback on messages) with tiered, granular signals
- Extends §8.3 (directionality as pre-processing) with derived knowledge and pattern-based enrichment
- Adds a new retrieval namespace (derived knowledge) alongside the existing KB and user sources
- Adds new entities to the data model (§8.4)
- Does **not** replace or modify any existing functionality

> **DISCLAIMER — Architecture integration**: The IIL sits as a layer on top of the existing RAG pipeline. It does NOT require changes to the core retrieval or generation logic. It adds a supplementary retrieval namespace and enriches the system prompt pre-processing step. The existing KB remains the primary authority (70% weight). All changes are additive.

---

## 1. System overview

### 1.1 Purpose

During the test phase, ScholarSync will be used by divergent user types:
- **Students** (normal 11th/12th class) — ask straightforward questions
- **Teachers** — ask curriculum-aligned questions, know the syllabus boundaries
- **Tutors** — ask deeper questions, test explanations from multiple angles
- **Subject Matter Experts (SMEs)** — drill down into concepts from dimensions students would never explore (misconceptions, cross-concept links, edge cases, real-world applications, exam traps)

The IIL captures all interactions, identifies high-value ones (especially from experts), curates them into a supplementary knowledge layer, and uses expert patterns to proactively enrich responses for all users. The Rich Feedback System provides the explicit signals that drive this flywheel.

### 1.2 Design principles

- **Capture everything, curate selectively**: 100% of interactions are logged. Only human-reviewed, approved artifacts enter the derived knowledge base.
- **KB is king**: The existing knowledge base (NCERT, board syllabi, tenant material) is always the primary retrieval source (70% weight). Derived knowledge supplements but never overrides.
- **Explicit feedback only (MVP)**: No implicit signal detection (rephrasing, copy behavior, dwell time) in this version. All feedback requires a deliberate user action.
- **Tiered by expertise**: Different user types see different feedback options. Students get simple, low-friction options. SMEs get the full expert panel.
- **Manual curation only (MVP)**: All derived knowledge artifacts require human review before entering the supplementary retrieval layer. No auto-approval.

### 1.3 What is NOT in scope

- Implicit feedback signals (behavioral detection like rephrasing, copy, dwell time)
- Auto-approval of curation candidates
- Outcome tracing (tracing exam improvement back to specific interactions)
- Model fine-tuning (this is retrieval enrichment, not model training)
- Changes to the core RAG retrieval or generation pipeline logic

---

## 2. Rich Feedback System

### 2.1 Overview

Every chat response in the platform shows feedback options to the user. The options shown depend on the user's expertise tier. Feedback is per-message (not per-conversation).

> **CAUTION**: The feedback UI must be lightweight and non-intrusive. Students should never feel like they're filling out a form. The primary options (helpful/not helpful) should be single-tap. Extended options appear only on demand.

### 2.2 User expertise tiers

A new field `expertise_tier` is added to the User entity.

| Tier | Value | Assigned by | Description |
|------|-------|-------------|-------------|
| Student | `student` | Default for student role | Normal 11th/12th class students |
| Teacher | `teacher` | Default for teacher role | School teachers within the tenant |
| Tutor | `tutor` | Platform admin assignment | External tutors invited for testing |
| SME | `sme` | Platform admin assignment | Subject matter experts invited for testing |

> **TECHNICAL NOTE**: The `expertise_tier` is separate from the existing RBAC `role`. A user can have role=Student but tier=sme (e.g., a student who is also a subject matter expert in a particular area, though this is unlikely). In practice, for the test phase, platform admin assigns tiers at user creation. The tier is stored on the User entity and is immutable by the user themselves.

> **PLUG-IN POINT**: The `expertise_tier` field can later be extended to support implicit tier detection (e.g., if a user consistently provides expert-validated feedback, their tier could be auto-upgraded). This is NOT in MVP scope.

### 2.3 Feedback signals — complete definition

#### 2.3.1 Tier 1 — Student signals (available to ALL tiers)

| Signal | Enum value | UI element | Free-text | Description |
|--------|-----------|------------|-----------|-------------|
| Helpful | `helpful` | Thumb-up icon | No | Response answered the question well. Basic positive signal. |
| Not helpful | `not_helpful` | Thumb-down icon | Optional (prompt: "What went wrong?") | Response didn't serve the user. |
| Confusing | `confusing` | Question-mark icon | No | Content may be correct but the explanation was hard to follow. |
| Incomplete | `incomplete` | Ellipsis icon | No | Response was correct but shallow — didn't cover enough. |

**UI behavior**: These four options appear as small icons below every assistant message. Single-tap to select. User can select ONE of these four (mutually exclusive). Selecting one highlights it and dims the others.

#### 2.3.2 Tier 2 — Teacher signals (available to teacher, tutor, SME)

| Signal | Enum value | UI element | Free-text | Description |
|--------|-----------|------------|-----------|-------------|
| Inaccurate | `inaccurate` | X-mark icon | Required (prompt: "What was incorrect?") | Factually wrong content. High-severity signal. |
| Off-syllabus | `off_syllabus` | Target icon | No | Content went beyond curriculum scope for this class/board. |

**UI behavior**: These appear when the user taps a "More feedback" link below the Tier 1 icons. They are additive — a teacher can mark something as both "helpful" AND "off-syllabus" (it was a good answer but went beyond what students need).

> **CAUTION**: "Inaccurate" is the highest-severity negative signal in the system. It MUST require free-text explaining what was wrong. This free-text feeds directly into quality alerts and prevents bad content from entering the derived KB.

#### 2.3.3 Tier 3 — SME signals (available to tutor and SME only)

| Signal | Enum value | UI element | Free-text | Description |
|--------|-----------|------------|-----------|-------------|
| Expert validated | `expert_validated` | Rosette/badge icon | No | SME confirms response is factually correct and well-structured. Strongest positive signal for curation. |
| Missing dimension | `missing_dimension` | Tag icon | No (but requires dimension_tag selection) | SME tags which angle/dimension was absent. Selects from the dimension taxonomy. |
| Expert note | `expert_note` | Note icon | Required (prompt: "Add your correction or addition") | Free-text correction, alternative explanation, or additional context. |

**UI behavior**: These appear in an expanded "Expert feedback" panel, visually distinct from the basic options. "Missing dimension" shows a dropdown/pill selector with the dimension taxonomy values. "Expert note" opens a text input area.

> **TECHNICAL NOTE**: "Missing dimension" requires a `dimension_tag` value from the dimension taxonomy (see §4.3). The UI should show this as a single-select dropdown or pill list. The SME can submit multiple "missing dimension" signals for the same message (e.g., both "misconceptions" and "exam_traps" were missing).

> **PLUG-IN POINT**: The "expert note" free-text itself becomes a curation candidate in Part 2 of the IIL. When processing curation candidates, expert notes should be treated as first-class artifacts, not just metadata.

### 2.4 Feedback data model

#### New entity: `InteractionFeedback`

```
InteractionFeedback
├── id                  UUID, PK
├── message_id          UUID, FK → Message, required
├── user_id             UUID, FK → User, required
├── user_tier           Enum (student, teacher, tutor, sme), required
│                       ↳ Snapshot of user's tier at time of feedback
├── signal_type         Enum (helpful, not_helpful, confusing, incomplete,
│                             inaccurate, off_syllabus, expert_validated,
│                             missing_dimension, expert_note), required
├── concept_node_id     UUID, FK → Concept, nullable
│                       ↳ Inherited from the interaction's concept mapping
├── dimension_tag       Enum (see §4.3), nullable
│                       ↳ Required when signal_type = missing_dimension
├── free_text           Text, nullable
│                       ↳ Required when signal_type IN (inaccurate, expert_note)
│                       ↳ Optional when signal_type = not_helpful
├── tenant_id           UUID, FK → Tenant, required
├── created_at          Timestamp, required
└── updated_at          Timestamp, required
```

**Constraints**:
- A user can submit multiple feedback signals for the same message (e.g., "helpful" + "missing_dimension")
- `user_tier` is snapshotted at feedback time (not a live lookup) so analytics remain accurate even if tiers change
- `concept_node_id` is populated automatically from the interaction log's concept mapping
- `tenant_id` is required for tenant isolation (standard ScholarSync pattern)

#### Indexes

- `(message_id, signal_type)` — for querying all feedback on a message
- `(concept_node_id, signal_type)` — for aggregating feedback per concept (feeds coverage map)
- `(user_tier, signal_type, created_at)` — for filtering expert feedback for curation
- `(tenant_id, created_at)` — for tenant-scoped analytics

### 2.5 Feedback API

```
POST   /api/v1/messages/{message_id}/feedback
       Body: { signal_type, dimension_tag?, free_text? }
       Auth: Bearer token (user must own the conversation or be in the same tenant)
       Response: 201 Created with feedback record

GET    /api/v1/messages/{message_id}/feedback
       Auth: Bearer token (own feedback only for students; all feedback for admin/platform)
       Response: List of InteractionFeedback records

DELETE /api/v1/messages/{message_id}/feedback/{feedback_id}
       Auth: Bearer token (own feedback only)
       Response: 204 No Content
```

> **CAUTION**: Students should only see their OWN feedback on a message. Teachers/admins can see aggregated feedback. SME feedback (especially expert notes) should be visible to platform admins for curation review.

### 2.6 Validation rules

| Rule | Enforcement |
|------|-------------|
| `inaccurate` requires `free_text` | API validation — reject 400 if missing |
| `expert_note` requires `free_text` | API validation — reject 400 if missing |
| `missing_dimension` requires `dimension_tag` | API validation — reject 400 if missing |
| Only tutor/sme can submit Tier 3 signals | API validation — reject 403 if tier insufficient |
| Only teacher/tutor/sme can submit Tier 2 signals | API validation — reject 403 if tier insufficient |
| `dimension_tag` must be from the taxonomy | API validation — reject 400 if invalid enum value |
| `user_tier` is server-derived, not client-submitted | Server populates from user profile, ignore client value |

---

## 3. Interaction Intelligence Layer — Part 1: Rich Interaction Logging

### 3.1 Overview

Every chat interaction is logged with structured metadata far beyond basic message storage. This is the raw material for all downstream intelligence.

> **CAUTION — MUST BE LIVE FROM DAY ONE**: You cannot retroactively enrich logs. If the structured metadata isn't captured from the first session, early SME interactions are permanently lost as training data. This is the P0 prerequisite for everything else.

### 3.2 Enhanced interaction log

#### New entity: `InteractionLog`

This is a structured record created for every assistant message in a chat. It is NOT a replacement for the existing Message entity — it is an analytics/intelligence overlay.

```
InteractionLog
├── id                      UUID, PK
├── message_id              UUID, FK → Message, required, unique
├── chat_id                 UUID, FK → Chat, required
├── notebook_id             UUID, FK → Notebook, required
├── user_id                 UUID, FK → User, required
├── user_tier               Enum (student, teacher, tutor, sme), required
├── tenant_id               UUID, FK → Tenant, required
│
│   ── Query metadata ──
├── query_text              Text, required
│                           ↳ The user's query that triggered this response
├── query_intent            Enum (factual, conceptual, application, analytical,
│                                 procedural, comparative), nullable
│                           ↳ Auto-classified by the system
├── concept_node_id         UUID, FK → Concept, nullable
│                           ↳ Which curriculum taxonomy node this maps to
├── conversation_position   Integer, required
│                           ↳ Position in the conversation (1 = first query)
├── is_followup             Boolean, required
│                           ↳ True if this continues the same concept as previous message
├── chain_depth             Integer, required
│                           ↳ How deep in a follow-up chain (1 = standalone, 2+ = follow-up)
│
│   ── Retrieval metadata ──
├── chunks_retrieved        JSONB, required
│                           ↳ Array of { chunk_id, source_id, relevance_score, source_type }
│                           ↳ source_type: "kb" | "user_source" | "derived"
├── retrieval_strategy      String, nullable
│                           ↳ e.g., "semantic", "hybrid", "multi-query"
├── kb_hit                  Boolean, required
│                           ↳ True if KB chunks were used in final context
├── derived_hit             Boolean, required, default false
│                           ↳ True if derived knowledge artifacts were used
├── fallback_triggered      Boolean, required
│                           ↳ True if hybrid augmentation was needed (out-of-KB)
│
│   ── Response metadata ──
├── response_token_count    Integer, required
├── citations_count         Integer, required
├── grounding_mode          Enum (strict, hybrid), required
├── out_of_kb_indicator     Boolean, required
│                           ↳ True if the response included the out-of-KB visual indicator
├── latency_ms              Integer, required
│                           ↳ Total response generation time
│
│   ── Timestamps ──
├── created_at              Timestamp, required
└── updated_at              Timestamp, required
```

> **TECHNICAL NOTE — Query intent classification**: The `query_intent` field is auto-classified by the system. For MVP, this can be a simple LLM-based classifier run asynchronously after the response is generated (not on the critical path). Categories: `factual` (what is X?), `conceptual` (why does X happen?), `application` (how do I use X?), `analytical` (compare X and Y), `procedural` (how to solve X?), `comparative` (difference between X and Y). If classification fails or confidence is low, leave nullable.

> **TECHNICAL NOTE — Concept node mapping**: The `concept_node_id` maps the interaction to the curriculum taxonomy (board → class → subject → chapter → concept). For Tutor-mode notebooks, this is directly available from the notebook's `curriculum_scope`. For Exploratory-mode notebooks, this requires auto-classification against the taxonomy. For MVP, this can run asynchronously and be nullable when classification is uncertain.

> **PLUG-IN POINT**: In future versions, this log can be extended with implicit signals (rephrasing detection, dwell time, copy events) without schema changes — add nullable columns.

### 3.3 Session chain linking

Follow-up queries within the same conversation are linked into chains. This is derived from the InteractionLog data, not a separate entity.

**Chain detection logic**:
1. If the current query's `concept_node_id` matches the previous message's `concept_node_id` → `is_followup = true`, `chain_depth = previous.chain_depth + 1`
2. If concept nodes differ or this is the first message → `is_followup = false`, `chain_depth = 1`
3. If concept classification is unavailable for either message → fall back to conversation position only

> **DISCLAIMER**: Chain depth is a critical signal for curation candidacy (Part 2). A chain depth of 3+ on the same concept, from an SME, is one of the strongest indicators of a valuable interaction. Getting this right matters.

### 3.4 Logging pipeline

The InteractionLog is populated as a post-processing step after each assistant message is generated and persisted:

1. Message is generated and persisted (existing flow — no changes)
2. Asynchronously (background task), create the InteractionLog record:
   - Query metadata: extract from the user message and conversation context
   - Retrieval metadata: extract from the pipeline trace (already captured per FR-STUDIO-4 / NFR-OBS-3)
   - Response metadata: extract from the generation result
   - Concept mapping: run taxonomy classifier if not in Tutor mode
   - Chain linking: compute from previous InteractionLog in the same chat

> **CAUTION**: The logging pipeline must NOT add latency to the chat response. All InteractionLog creation is asynchronous. If the logging task fails, the chat response is still delivered — log creation failures are captured in observability (NFR-OBS-1) but do not affect the user experience.

### 3.5 Indexes

- `(concept_node_id, user_tier, created_at)` — primary query path for curation candidate scanning
- `(chat_id, conversation_position)` — for chain reconstruction
- `(user_tier, chain_depth, created_at)` — for finding deep expert explorations
- `(tenant_id, created_at)` — for tenant-scoped analytics
- `(notebook_id)` — for notebook-level analytics

---

## 4. Interaction Intelligence Layer — Part 2: Derived Knowledge Curation

### 4.1 Overview

High-value interactions (especially from SMEs) are curated into "derived knowledge artifacts" — a new supplementary retrieval layer. This is the core flywheel: one expert's deep exploration benefits every subsequent student.

**Flow**: Candidate identification → Artifact extraction → Human review → Embedding & indexing → Retrieval blending

> **DISCLAIMER — Manual review is mandatory**: In MVP, every derived knowledge artifact must be reviewed and approved by a human (platform admin or designated SME reviewer) before it enters the supplementary retrieval namespace. There is NO auto-approval path.

### 4.2 Curation candidate identification

The system continuously scans InteractionLog records and flags candidates for curation based on a scoring formula.

#### Candidate scoring signals

| Signal | Weight | Source | Description |
|--------|--------|--------|-------------|
| User tier = SME | +3 | InteractionLog.user_tier | Highest expertise tier |
| User tier = tutor | +2 | InteractionLog.user_tier | High expertise tier |
| User tier = teacher | +1 | InteractionLog.user_tier | Moderate expertise tier |
| Expert-validated feedback | +4 | InteractionFeedback.signal_type | Strongest positive signal |
| Helpful feedback from high-tier user | +2 | InteractionFeedback | Positive signal with authority |
| Chain depth ≥ 3 on same concept | +2 | InteractionLog.chain_depth | Deep exploration |
| Novel query angle | +1 | Computed: no prior log with same concept + intent combo | New dimension explored |
| Inaccurate feedback | -10 (hard reject) | InteractionFeedback.signal_type | Factual error flagged |

**Candidate threshold**: Score ≥ 5 → flagged as candidate for review.

> **TECHNICAL NOTE**: The scoring engine runs as a background job (e.g., cron every 15 minutes, or event-driven on feedback submission). It does NOT run on the chat critical path. Candidates are written to the CurationCandidate entity (see §4.5).

> **TECHNICAL NOTE — Novel query angle detection**: For MVP, "novel" is defined as: no prior InteractionLog exists for the same `concept_node_id` with the same `query_intent`. Example: if "Electromagnetic Induction" has logs with `factual` and `conceptual` intents, but an SME submits an `application` intent query, that's novel. This is a simple approximation; more sophisticated novelty detection can be added later.

### 4.3 Dimension taxonomy

A lightweight, controlled vocabulary for tagging HOW a concept was explored. This is a separate list from the curriculum taxonomy.

| Dimension | Enum value | Description |
|-----------|-----------|-------------|
| Core definition | `definition` | Basic explanation of what the concept is |
| Intuition & analogy | `intuition` | Intuitive understanding, analogies, mental models |
| Common misconceptions | `misconceptions` | What students typically get wrong |
| Real-world applications | `applications` | How this concept appears in the real world |
| Cross-concept links | `cross_concept` | Connections to other concepts in the curriculum |
| Mathematical treatment | `mathematical` | Formulas, derivations, numerical problem-solving |
| Historical context | `historical` | How this concept was discovered, evolved |
| Exam patterns & traps | `exam_traps` | Common exam question patterns, tricks, trap answers |
| Visual & diagrammatic | `visual` | Diagrams, graphs, visual representations |
| Problem-solving strategies | `problem_solving` | Step-by-step approaches, shortcuts, heuristics |

> **PLUG-IN POINT**: This taxonomy is deliberately lightweight (10 values). It can be extended as the test phase reveals gaps. Adding a new value is a simple enum extension + migration, no structural changes needed.

> **CAUTION**: The dimension taxonomy is NOT the same as the curriculum taxonomy (board → class → subject → chapter → concept). They serve different purposes. The curriculum taxonomy says WHAT the concept is. The dimension taxonomy says HOW it was explored.

### 4.4 Artifact extraction

When a candidate is approved for review, the system extracts a structured "derived knowledge artifact" from the interaction.

**Extraction process** (LLM-assisted):

1. Take the full conversation chain (all messages in the chain, not just the flagged message)
2. Send to LLM with a structured extraction prompt:
   - Distill the Q&A into a clean, standalone explanation
   - Identify the dimension(s) it covers (from the taxonomy)
   - Ensure the explanation is self-contained (doesn't require conversation context)
   - Maintain factual accuracy (the explanation must be consistent with KB content)
   - Tag the concept node it maps to
3. Output: a structured DerivedKnowledgeArtifact (see §4.5)

> **CAUTION — Extraction prompt**: The extraction prompt must explicitly instruct the LLM to: (a) not introduce new facts beyond what's in the interaction + KB, (b) maintain age-appropriate language for 11th/12th class students, (c) preserve the multi-dimensional nature of the expert's exploration. The prompt template should be versioned and centrally maintained (same pattern as FR-PERS-4).

**For expert notes** (from the feedback system):

Expert notes submitted via the "expert_note" feedback signal follow a slightly different path:
1. The note itself is the artifact content (no extraction needed)
2. Concept node is inherited from the interaction log
3. Dimension tag may be inferred or left for the reviewer to assign
4. Still requires human review before entering the derived KB

### 4.5 Data model — Curation entities

#### CurationCandidate

```
CurationCandidate
├── id                      UUID, PK
├── interaction_log_id      UUID, FK → InteractionLog, required
│                           ↳ Or feedback_id for expert notes
├── source_type             Enum (interaction_chain, expert_note), required
├── candidate_score         Float, required
├── scoring_signals         JSONB, required
│                           ↳ Breakdown of which signals contributed to the score
├── concept_node_id         UUID, FK → Concept, required
├── status                  Enum (pending, in_review, approved, rejected), required
│                           ↳ Default: pending
├── reviewed_by             UUID, FK → User, nullable
├── reviewed_at             Timestamp, nullable
├── review_notes            Text, nullable
├── tenant_id               UUID, FK → Tenant, required
├── created_at              Timestamp, required
└── updated_at              Timestamp, required
```

#### DerivedKnowledgeArtifact

```
DerivedKnowledgeArtifact
├── id                      UUID, PK
├── candidate_id            UUID, FK → CurationCandidate, required
├── concept_node_id         UUID, FK → Concept, required
├── dimension_tags          Array<Enum>, required
│                           ↳ One or more dimensions from the taxonomy
├── content                 Text, required
│                           ↳ The distilled, standalone explanation
├── source_interaction_ids  Array<UUID>, required
│                           ↳ References to the original InteractionLog records
├── source_user_tier        Enum (student, teacher, tutor, sme), required
│                           ↳ Tier of the user who generated the original interaction
├── confidence_score        Float, nullable
│                           ↳ Reviewer-assigned quality score (1-5)
├── embedding_id            String, nullable
│                           ↳ Reference to the vector embedding in the derived namespace
├── is_active               Boolean, required, default true
│                           ↳ Can be deactivated without deletion
├── tenant_id               UUID, FK → Tenant, required
├── created_at              Timestamp, required
└── updated_at              Timestamp, required
```

### 4.6 Retrieval blending

Once a DerivedKnowledgeArtifact is approved and embedded, it becomes available in the retrieval pipeline.

**Retrieval architecture**:

The existing retrieval pipeline is extended with a third retrieval namespace:

1. **KB namespace** (existing) — NCERT, board syllabi, tenant proprietary material. Weight: **70%**
2. **User sources namespace** (existing) — user-uploaded documents in their notebook. Weight: contextual (used when sources are selected)
3. **Derived knowledge namespace** (NEW) — curated expert interaction artifacts. Weight: **30%**

**Blending logic**:

```
retrieve(query, concept_node, notebook_mode):
  1. kb_results = retrieve_from_kb(query, concept_node, top_k=10)
  2. IF notebook_mode == "exploratory" AND sources_selected:
       user_results = retrieve_from_user_sources(query, top_k=5)
  3. derived_results = retrieve_from_derived(query, concept_node, top_k=5)
  4. merged = blend(kb_results, user_results, derived_results, weights=[0.7, contextual, 0.3])
  5. RETURN top_k from merged by blended score
```

> **TECHNICAL NOTE — Derived namespace isolation**: The derived knowledge namespace must be isolated by tenant (like all other namespaces). However, for the test phase where there's a single tenant, global derived artifacts are acceptable. Multi-tenant derived knowledge sharing is a future consideration.

> **TECHNICAL NOTE — Concept-scoped retrieval**: When retrieving from the derived namespace, results should be filtered to the same `concept_node_id` or its parent chapter. This prevents cross-concept pollution. If the concept node is unknown (Exploratory mode without classification), retrieve without concept filtering.

> **CAUTION — Blending weights are configurable**: The 70/30 split is the starting configuration. Platform admin should be able to adjust these weights (stored in tenant config, not hard-coded). During the test phase, monitor whether derived content is helping or hurting response quality — feedback signals will tell you.

### 4.7 Concept coverage map

The system maintains a per-concept view of which dimensions have derived artifacts.

**Computation**: For each concept node in the curriculum taxonomy, count the number of active DerivedKnowledgeArtifact records per dimension tag. This is a materialized view / cached computation, not a separate entity.

```sql
-- Concept coverage map query
SELECT
  c.id AS concept_node_id,
  c.name AS concept_name,
  dka.dimension_tag,
  COUNT(dka.id) AS artifact_count,
  AVG(dka.confidence_score) AS avg_confidence
FROM concept c
LEFT JOIN derived_knowledge_artifact dka
  ON dka.concept_node_id = c.id AND dka.is_active = true
GROUP BY c.id, c.name, dka.dimension_tag
ORDER BY c.id, dka.dimension_tag;
```

**Admin view**: A simple matrix (concept × dimension) showing fill status. Cells with 0 artifacts are gaps. This view is available to Platform Admin.

> **PLUG-IN POINT**: The coverage map directly informs SME test planning. Platform admin can assign SMEs to explore specific concept × dimension gaps: "Newton's Laws has strong coverage on misconceptions but zero on cross-concept links — explore that angle."

### 4.8 Curation review API

```
GET    /api/v1/admin/curation/candidates
       Query params: status, concept_node_id, min_score, user_tier
       Auth: Platform admin only
       Response: Paginated list of CurationCandidate with nested InteractionLog data

GET    /api/v1/admin/curation/candidates/{id}
       Auth: Platform admin only
       Response: Full candidate with interaction chain, feedback signals, and extracted artifact preview

POST   /api/v1/admin/curation/candidates/{id}/review
       Body: { decision: "approved" | "rejected", review_notes?, confidence_score? (1-5) }
       Auth: Platform admin only
       Response: Updated candidate + if approved, triggers artifact extraction and embedding

GET    /api/v1/admin/curation/coverage-map
       Query params: board, class, subject
       Auth: Platform admin only
       Response: Concept × dimension matrix with artifact counts

GET    /api/v1/admin/curation/artifacts
       Query params: concept_node_id, dimension_tag, is_active
       Auth: Platform admin only
       Response: Paginated list of DerivedKnowledgeArtifact

PATCH  /api/v1/admin/curation/artifacts/{id}
       Body: { is_active?, content?, dimension_tags? }
       Auth: Platform admin only
       Response: Updated artifact (content edits trigger re-embedding)
```

---

## 5. Interaction Intelligence Layer — Part 3: Query Pattern Augmentation

### 5.1 Overview

Expert questioning patterns are captured and used to: (a) generate richer starter prompts for focus cards, and (b) proactively enrich system prompts so responses surface multiple dimensions even for simple student queries.

### 5.2 Exploration template extraction

From SME/tutor conversation chains (chain depth ≥ 3), extract the questioning pattern.

**Extraction process** (LLM-assisted, background job):

1. Take all InteractionLog records in a chain where `user_tier IN (sme, tutor)` and `chain_depth >= 3`
2. Send to LLM with extraction prompt:
   - Identify the sequence of query intents (e.g., factual → application → misconception → cross-concept)
   - Extract the dimension progression (which dimensions were explored, in what order)
   - Generate 3-5 "template prompts" — generalized versions of the expert's questions that could be reused for other concepts in the same subject
3. Output: an ExplorationTemplate record

#### ExplorationTemplate

```
ExplorationTemplate
├── id                      UUID, PK
├── concept_node_id         UUID, FK → Concept, required
├── source_chain_ids        Array<UUID>, required
│                           ↳ InteractionLog IDs that formed the chain
├── source_user_tier        Enum (tutor, sme), required
├── dimension_sequence      Array<Enum>, required
│                           ↳ Ordered list of dimensions explored
├── template_prompts        JSONB, required
│                           ↳ Array of { prompt_text, target_dimension, personalization_hint }
├── is_active               Boolean, required, default true
├── tenant_id               UUID, FK → Tenant, required
├── created_at              Timestamp, required
└── updated_at              Timestamp, required
```

> **DISCLAIMER**: Exploration templates are extracted asynchronously and do NOT require human review (unlike derived knowledge artifacts). They are prompt suggestions, not factual content — the response generation still runs through the full RAG pipeline with KB grounding.

### 5.3 Starter prompt enrichment

Exploration templates feed directly into the focus card generation (FR-DIR-3).

**Current behavior** (FR-DIR-3): Focus cards include 3-5 LLM-generated starter prompts.

**Enhanced behavior**: When generating starter prompts for a concept that has exploration templates:

1. Retrieve all ExplorationTemplates for the concept
2. Extract `template_prompts` and their `target_dimension` values
3. Include them as examples/seeds in the starter prompt generation system prompt
4. The LLM generates 3-5 prompts that reflect expert-validated exploration angles, personalized with the student's interest profile

> **PLUG-IN POINT**: This integrates with FR-DIR-3 and FR-PERS-3. The exploration template prompts are input to the same personalization prompt template that already governs starter prompt generation. No new generation pipeline needed.

### 5.4 Proactive response enrichment

When a student asks a simple question about a concept that has rich exploration data, the system prompt is enriched to proactively surface additional dimensions.

**Implementation** (extends §8.3 — directionality as pre-processing):

1. Student sends a query in Tutor mode (or a classified concept in Exploratory mode)
2. Pre-processing step looks up:
   - Derived knowledge artifacts for this concept (from Part 2)
   - Exploration templates for this concept (from Part 3)
   - Coverage map: which dimensions have strong coverage
3. If ≥ 2 dimensions have derived artifacts, add a directive to the system prompt:

```
When answering this question, also briefly mention:
- [dimension with highest artifact confidence]: [1-line summary from derived artifact]
- [second dimension]: [1-line summary from derived artifact]
Do not force these if they don't fit naturally. They should feel like a helpful addition, not a tangent.
```

> **CAUTION — Don't overload**: Proactive enrichment should add at most 1-2 additional dimensions. More than that makes responses feel bloated. Prioritize dimensions by: (a) feedback engagement data (if available), (b) artifact confidence score, (c) dimension type (misconceptions and exam_traps tend to be highest-value for students).

> **CAUTION — Scope boundary**: Proactive enrichment must respect the off-syllabus guardrail. If a derived artifact was tagged as off-syllabus by feedback, do NOT include it in enrichment.

### 5.5 Feedback-driven enrichment refinement (future)

> **PLUG-IN POINT — NOT IN MVP**: In future versions, track which proactively surfaced dimensions students engage with (follow-up questions on that dimension) vs ignore. Over time, this tunes enrichment priority per concept — the system learns what's valuable for students, not just what experts found interesting.

---

## 6. Implementation priorities

### 6.1 Priority matrix

| Priority | Component | What to build | Effort | Blocks |
|----------|-----------|---------------|--------|--------|
| P0 | InteractionLog schema + pipeline | Entity, async logging pipeline, indexes | Medium | Everything in Part 2 and 3 |
| P0 | User expertise tier | Field on User entity, admin assignment UI | Low | Feedback tiering, curation scoring |
| P0 | InteractionFeedback entity + API | Entity, tiered UI, validation, API | Medium | Curation candidate scoring |
| P0 | Feedback UI (tiered) | Frontend component on every assistant message | Medium | User testing data collection |
| P1 | Derived knowledge namespace | New vector namespace, embedding pipeline | Medium | Retrieval blending |
| P1 | CurationCandidate + scoring engine | Entity, background scoring job, candidate flagging | Medium | Curation review |
| P1 | Curation review admin UI | Candidate list, detail view, approve/reject | Medium | Getting artifacts into derived KB |
| P1 | DerivedKnowledgeArtifact entity + extraction | Entity, LLM extraction pipeline, embedding | Medium | Retrieval blending |
| P1 | Retrieval blending | Extend retrieval pipeline with derived namespace, configurable weights | Medium | Responses using derived knowledge |
| P1 | Dimension taxonomy | Enum definition, migration | Low | Consistent tagging |
| P2 | Concept coverage map | Materialized view/query, admin UI | Low | SME test planning |
| P2 | ExplorationTemplate extraction | Entity, LLM extraction background job | Medium | Starter prompt enrichment |
| P2 | Starter prompt enrichment | Extend FR-DIR-3 generation with template data | Low | Better focus card prompts |
| P2 | Proactive response enrichment | Extend §8.3 pre-processing with derived knowledge | Medium | Multi-dimensional responses |

### 6.2 Build sequence

**Phase 1 — Foundation (before test users arrive)**:
All P0 items. The platform must be capturing rich interaction logs and tiered feedback from the first session.

**Phase 2 — Flywheel (first 2-4 weeks of testing)**:
All P1 items. As interactions accumulate, the curation pipeline processes candidates and starts populating the derived knowledge namespace.

**Phase 3 — Multiplier (weeks 4-8 of testing)**:
All P2 items. Enough data exists to extract patterns and enrich responses proactively.

---

## 7. Observability & monitoring

### 7.1 Metrics to track

| Metric | Source | Dashboard |
|--------|--------|-----------|
| Interaction logs created per day (by tier) | InteractionLog | Admin |
| Feedback signals per day (by type, by tier) | InteractionFeedback | Admin |
| Curation candidates flagged per week | CurationCandidate | Admin |
| Candidates approved vs rejected ratio | CurationCandidate | Admin |
| Derived artifacts per concept | DerivedKnowledgeArtifact | Coverage map |
| Retrieval blending: derived_hit rate | InteractionLog.derived_hit | Admin |
| Inaccurate feedback rate per concept | InteractionFeedback | Quality alert |
| Average chain depth by user tier | InteractionLog | Admin |

### 7.2 Alerts

| Alert | Trigger | Severity |
|-------|---------|----------|
| High inaccuracy rate | > 3 "inaccurate" signals on same concept in 24h | High |
| Logging pipeline failure | InteractionLog creation failures > 1% | High |
| Curation queue backlog | > 50 pending candidates older than 7 days | Medium |
| Zero feedback | No feedback signals received in 24h during active testing | Medium |

---

## 8. Testing requirements

### 8.1 Unit tests

- Feedback validation rules (tier enforcement, required fields)
- Candidate scoring formula (verify score computation with known inputs)
- Chain linking logic (follow-up detection, depth computation)
- Retrieval blending weights (verify 70/30 split in merged results)

### 8.2 Integration tests

- End-to-end: chat → interaction log → feedback → candidate → review → artifact → retrieval blending → enriched response
- Tier enforcement: student cannot submit expert_validated feedback
- Tenant isolation: derived artifacts from tenant A are not retrievable by tenant B
- Concept scoping: derived artifacts for concept X don't pollute retrieval for concept Y

### 8.3 Manual validation (during test phase)

- Platform admin reviews curation candidates weekly
- Spot-check derived artifact quality (factual accuracy, age-appropriateness)
- Monitor coverage map for balanced dimension coverage
- Verify that enriched responses feel natural and not forced

---

## 9. Appendix

### 9.1 Glossary of new terms

| Term | Definition |
|------|-----------|
| Interaction Intelligence Layer (IIL) | The three-part system (logging, curation, augmentation) that makes the RAG continuously smarter from user interactions |
| Expertise tier | A user classification (student, teacher, tutor, sme) that determines feedback options and interaction weight |
| Derived knowledge artifact | A curated, structured explanation extracted from high-value interactions, embedded into a supplementary retrieval namespace |
| Dimension taxonomy | A controlled vocabulary for how a concept was explored (misconceptions, applications, exam traps, etc.) |
| Exploration template | A captured expert questioning pattern per concept, used to generate better starter prompts |
| Concept coverage map | A matrix showing which concepts have derived artifacts for which dimensions |
| Curation candidate | An interaction flagged by the scoring engine as potentially valuable for the derived KB |

### 9.2 Entity relationship summary

```
User (existing)
  └── expertise_tier (NEW field)

Message (existing)
  ├── InteractionLog (NEW, 1:1)
  │     └── concept_node_id → Concept (existing)
  └── InteractionFeedback (NEW, 1:many)
        ├── concept_node_id → Concept
        └── dimension_tag → DimensionTaxonomy

InteractionLog
  └── CurationCandidate (1:0..1)
        └── DerivedKnowledgeArtifact (1:0..1)
              └── concept_node_id → Concept

Concept (existing)
  ├── DerivedKnowledgeArtifact (1:many)
  └── ExplorationTemplate (1:many)
```

### 9.3 Configuration parameters

| Parameter | Default | Configurable by | Description |
|-----------|---------|----------------|-------------|
| `iil.blending.kb_weight` | 0.7 | Platform admin | KB retrieval weight in blending |
| `iil.blending.derived_weight` | 0.3 | Platform admin | Derived knowledge retrieval weight |
| `iil.curation.candidate_threshold` | 5 | Platform admin | Minimum score to flag as candidate |
| `iil.curation.scoring_interval_minutes` | 15 | Dev config | How often the scoring engine runs |
| `iil.enrichment.max_dimensions` | 2 | Platform admin | Max proactive dimensions per response |
| `iil.logging.async_timeout_ms` | 5000 | Dev config | Timeout for async log creation |

---

*End of specification.*
