## 15. Studio Fallback Task Prompt (Legacy)

| Field | Value |
|-------|-------|
| Dataset ID | `studio_fallback_legacy` |
| Category | Studio |
| Tier | Tier 2 → regression subset |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.3.0 |

**Agent responsibility:** **Regression safety net** when the primary Studio task J2 template is missing from disk (`FileNotFoundError` in `StudioService._load_prompt_template()`). Normal Studio flow uses rich templates (Agents 11–14) plus the shared system prompt (Agent 10). In fallback mode the **user/task prompt** loads `studio/fallback_task_prompt.j2` v1.3.0 (self-contained output contract), and generation must still return a **complete, parseable artifact**: quiz JSON object, flashcards JSON array, mind-map Markdown, or slide-deck Markdown — not a one-sentence outline. This agent is **not** the primary product path; it ensures deployments missing a template file degrade gracefully instead of crashing.

**Audit finding (baseline v1.0.0):** v1.3.0 replaces the one-line fallback with a **self-contained production fallback J2** (task_type output contracts, grounding rules, empty-context handling) and wires it in `StudioService._load_prompt_template()` on `FileNotFoundError`. v1.2.0 had full eval gold but a minimal one-line production prompt.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `quiz_fallback` | task_type=quiz with/without context | 4 |
| `flashcards_fallback` | flashcards with/without context | 4 |
| `mind_map_fallback` | mind_map with/without context | 4 |
| `slide_deck_fallback` | slide_deck with/without context | 3 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **legacy_path** — Exercises FileNotFoundError fallback — minimal user prompt still runs.
* **graceful_output** — Full artifact returned; never a vague one-line outline.
* **no_crash** — Missing J2 does not abort Studio generation.
* **task_type_honored** — quiz→JSON object, flashcards→JSON array, mind_map/slide_deck→Markdown.
* **schema_valid** — Quiz/flashcard gold parses and passes structure validators.
* **grounding** — With context: facts from excerpt only; empty context: general or insufficient-source pattern.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `task_type`, `context`
* Output keys: `output` (full JSON string or Markdown body)

**Prompt template (production — legacy fallback J2 v1.3.0):**

```jinja2
You are in LEGACY FALLBACK mode — the primary Studio task template file is missing from disk.

Normal Studio uses rich per-task templates (Agents 11–14) plus the shared Agent 10 system prompt.
This fallback user/task prompt must still produce a complete, parseable artifact — never a one-line outline.

Inputs:
- task_type: {{ task_type }} (one of quiz | flashcards | mind_map | slide_deck)
- context: retrieved NCERT/source excerpt below, or empty

Non-negotiable rules:
1. Honor task_type — never return the wrong artifact shape.
2. Ground all facts in context when context is non-empty; do not invent page numbers, figure numbers, or citations.
3. When context is empty, produce a small coherent general-education artifact (quiz/flashcards) or an explicit insufficient-source mind map — never fabricate chapter-specific facts.
4. Match production validators used by Agents 11–14.
5. Return ONLY the artifact body — no preamble, no markdown fences around JSON, no postscript.

Per task_type output contract:

**quiz** → ONE valid JSON object only:
{
  "title": "...",
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "exact option string",
      "explanation": "1-2 sentences grounded in context"
    }
  ]
}
- 3–7 questions when context supports it; 3 minimum for thin/empty context.
- Exactly 4 options per question; correct_answer must match one option exactly.

**flashcards** → ONE valid JSON array only:
[{"front": "...", "back": "..."}, ...]
- 3–8 cards from context density; empty context → 3 general study-skills cards max.

**mind_map** → Markdown only (no JSON):
- Exactly one `#` hub; `##` / `###` branches; bullets under branches.
- Empty context → `# Insufficient source text` with honest next-step bullets.

**slide_deck** → Markdown only:
- Headings `# Slide N: Title`; 1–7 bullets per slide; final slide is conclusion.
- 3–6 slides typical; empty context → generic study-skills deck allowed.

{% if custom_instructions and custom_instructions.strip() %}
Custom instructions (format/tone only — do not override task_type shape):
{{ custom_instructions }}
{% endif %}

Source excerpt:
{% if context and context.strip() %}
{{ context }}
{% else %}
(empty — apply empty-context rules above)
{% endif %}

Generate the complete {{ task_type }} artifact now.
```

**Supplementary eval notes:**

```text
Supplementary eval notes (contract embedded in `studio/fallback_task_prompt.j2` v1.3.0):

- Pairs with **Agent 10** system prompt (`studio/system_educational_json_markdown.j2`) at runtime.
- Loaded via `StudioService._load_prompt_template()` on `FileNotFoundError` — not the primary happy path.
- LangSmith gold must be **full JSON/Markdown bodies**, not one-line outlines.
- Input keys: `task_type`, `context` (optional `custom_instructions` at runtime).
```

*Runtime note:* On `FileNotFoundError`, `StudioService._load_prompt_template()` loads `studio/fallback_task_prompt.j2` v1.3.0 via `load_prompt(task_type, context, custom_instructions)`. Structured generation still uses the **Agent 10 system prompt**. Eval gold requires **full production-shaped bodies**, not outlines.

**Why this agent is needed**

1. **Deployment safety** — a missing `quiz_prompt.j2` (or similar) must not break Studio.
2. **Shape regression** — even with a tiny prompt, output must remain valid quiz JSON / flashcard array / Markdown.
3. **Contrast with Agents 11–14** — those agents test the **happy path** with full instructions; Agent 15 tests **worst-case prompt starvation**.

> **Legacy notice:** Primary Studio always uses Agents 11–14 templates when files exist on disk.

### Evaluation examples (15)
## Variation: `quiz_fallback`


#### Example 1: `studio_fallback_legacy-001`

- **Variation:** quiz_fallback
- **Tags:** legacy, quiz
- **output_format:** JSON

**Inputs**

**Task Type:**

quiz

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Expected output**

**Output:**

{
  "title": "Current Electricity — Fallback Quiz",
  "questions": [
    {
      "question": "According to Ohm's law, if R doubles at constant V, current becomes:",
      "options": [
        "Doubled",
        "Halved",
        "Unchanged",
        "Zero"
      ],
      "correct_answer": "Halved",
      "explanation": "I=V/R so current halves when R doubles."
    },
    {
      "question": "Two resistors 4 Ω and 12 Ω in series give R_eq of:",
      "options": [
        "3 Ω",
        "16 Ω",
        "48 Ω",
        "8 Ω"
      ],
      "correct_answer": "16 Ω",
      "explanation": "Series resistances add: 4+12=16 Ω."
    },
    {
      "question": "Kirchhoff's junction rule states:",
      "options": [
        "Sum I in equals sum I out",
        "Sum V equals zero",
        "Power is conserved",
        "Charge is created"
      ],
      "correct_answer": "Sum I in equals sum I out",
      "explanation": "Current into a node equals current leaving."
    },
    {
      "question": "Drift velocity v_d relates to current by:",
      "options": [
        "I=neAv_d",
        "I=v_d/e",
        "I=ρv_d",
        "I=n/v_d"
      ],
      "correct_answer": "I=neAv_d",
      "explanation": "Microscopic form I=neAv_d."
    },
    {
      "question": "Resistivity ρ depends on:",
      "options": [
        "Material and temperature",
        "Length only",
        "Voltage only",
        "Current direction"
      ],
      "correct_answer": "Material and temperature",
      "explanation": "ρ is material property; metals increase ρ with T."
    }
  ]
}

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 2: `studio_fallback_legacy-005`

- **Variation:** quiz_fallback
- **Tags:** legacy, no_source
- **output_format:** JSON

**Inputs**

**Task Type:**

quiz

**Context:**



**Expected output**

**Output:**

{
  "title": "General Science Baseline (No Source)",
  "questions": [
    {
      "question": "SI unit of force is:",
      "options": [
        "Newton",
        "Joule",
        "Watt",
        "Pascal"
      ],
      "correct_answer": "Newton",
      "explanation": "Newton is the SI unit of force."
    },
    {
      "question": "Water chemical formula:",
      "options": [
        "H2O",
        "CO2",
        "NaCl",
        "O2 only"
      ],
      "correct_answer": "H2O",
      "explanation": "Water is dihydrogen monoxide."
    },
    {
      "question": "Safe lab practice includes:",
      "options": [
        "Reading labels before use",
        "Tasting chemicals",
        "Skipping goggles",
        "Random mixing"
      ],
      "correct_answer": "Reading labels before use",
      "explanation": "Basic laboratory safety."
    }
  ]
}

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass. no_source_general: pass.

---

#### Example 3: `studio_fallback_legacy-009`

- **Variation:** quiz_fallback
- **Tags:** legacy, quiz, source_pdf:lech105
- **output_format:** JSON

**Inputs**

**Task Type:**

quiz

**Context:**

Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.

**Expected output**

**Output:**

{
  "title": "Coordination Compounds — Fallback Quiz",
  "questions": [
    {
      "question": "Coordination number counts:",
      "options": [
        "σ-donor atoms on metal",
        "Total ligand mass",
        "Oxidation state only",
        "Electrons in metal"
      ],
      "correct_answer": "σ-donor atoms on metal",
      "explanation": "CN = donor atoms bonded to metal."
    },
    {
      "question": "[Fe(CN)6]4− has coordination number:",
      "options": [
        "4",
        "6",
        "8",
        "2"
      ],
      "correct_answer": "6",
      "explanation": "Six cyanide ligands → CN = 6."
    },
    {
      "question": "IUPAC ligand order is:",
      "options": [
        "Alphabetical",
        "By charge only",
        "Random",
        "By metal symbol"
      ],
      "correct_answer": "Alphabetical",
      "explanation": "IUPAC lists ligands alphabetically."
    },
    {
      "question": "Anionic ligands in IUPAC end in:",
      "options": [
        "-o suffix",
        "-ide always",
        "-ate only",
        "No suffix"
      ],
      "correct_answer": "-o suffix",
      "explanation": "Anionic ligands take -o."
    }
  ]
}

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 4: `studio_fallback_legacy-013`

- **Variation:** quiz_fallback
- **Tags:** legacy, no_source, neet
- **output_format:** JSON

**Inputs**

**Task Type:**

quiz

**Context:**



**Expected output**

**Output:**

{
  "title": "NEET Exam Strategy (No Chapter Source)",
  "questions": [
    {
      "question": "Best use of first 5 minutes in NEET?",
      "options": [
        "Scan paper and mark easy questions",
        "Solve hardest first always",
        "Skip OMR planning",
        "Ignore time sections"
      ],
      "correct_answer": "Scan paper and mark easy questions",
      "explanation": "Time management strategy."
    },
    {
      "question": "OMR filling should be:",
      "options": [
        "Clear single bubbles without stray marks",
        "Multiple bubbles per question",
        "Done only at home",
        "Ignored until end always"
      ],
      "correct_answer": "Clear single bubbles without stray marks",
      "explanation": "OMR discipline."
    },
    {
      "question": "Negative marking means:",
      "options": [
        "Wrong answers can reduce score",
        "All guesses are free",
        "Only biology penalized",
        "No effect on total"
      ],
      "correct_answer": "Wrong answers can reduce score",
      "explanation": "NEET negative-marking awareness."
    },
    {
      "question": "After a tough question you should:",
      "options": [
        "Move on and return if time permits",
        "Stop the entire paper",
        "Erase all answers",
        "Leave exam hall"
      ],
      "correct_answer": "Move on and return if time permits",
      "explanation": "Exam pacing tactic."
    }
  ]
}

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass. no_source_general: pass.

---

## Variation: `flashcards_fallback`


#### Example 1: `studio_fallback_legacy-002`

- **Variation:** flashcards_fallback
- **Tags:** legacy, flashcards
- **output_format:** JSON

**Inputs**

**Task Type:**

flashcards

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Expected output**

**Output:**

[
  {
    "front": "Where does salivary amylase act?",
    "back": "Mouth — starts starch digestion."
  },
  {
    "front": "Pepsin needs which stomach condition?",
    "back": "Acidic HCl medium."
  },
  {
    "front": "Trypsin enters duodenum via?",
    "back": "Pancreatic juice."
  },
  {
    "front": "Lipase digests?",
    "back": "Fats."
  },
  {
    "front": "Main nutrient absorption site?",
    "back": "Small intestine villi."
  }
]

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 2: `studio_fallback_legacy-006`

- **Variation:** flashcards_fallback
- **Tags:** legacy, no_source
- **output_format:** JSON

**Inputs**

**Task Type:**

flashcards

**Context:**



**Expected output**

**Output:**

[
  {
    "front": "Active recall?",
    "back": "Test yourself instead of only re-reading notes."
  },
  {
    "front": "Spaced repetition?",
    "back": "Review at intervals to strengthen long-term memory."
  },
  {
    "front": "Timed practice?",
    "back": "Simulate exam conditions to find weak topics."
  }
]

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass. no_source_general: pass.

---

#### Example 3: `studio_fallback_legacy-010`

- **Variation:** flashcards_fallback
- **Tags:** legacy, flashcards, source_pdf:keph106
- **output_format:** JSON

**Inputs**

**Task Type:**

flashcards

**Context:**

Torque τ=rF sin θ. τ=Iα. Parallel axis: I=I_cm+Md².

**Expected output**

**Output:**

[
  {
    "front": "Torque magnitude?",
    "back": "τ = rF sin θ"
  },
  {
    "front": "Rotational analog of F=ma?",
    "back": "τ = Iα"
  },
  {
    "front": "Parallel axis theorem?",
    "back": "I = I_cm + Md²"
  },
  {
    "front": "Door push near hinges vs handle?",
    "back": "Smaller lever arm → less torque for same F"
  }
]

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 4: `studio_fallback_legacy-014`

- **Variation:** flashcards_fallback
- **Tags:** legacy, flashcards, source_pdf:kemh107
- **output_format:** JSON

**Inputs**

**Task Type:**

flashcards

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd.

**Expected output**

**Output:**

[
  {
    "front": "Binomial general term?",
    "back": "Tr+1 = nCr a^(n−r) b^r"
  },
  {
    "front": "nCr in expansion means?",
    "back": "Combination count in (a+b)^n."
  }
]

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

## Variation: `mind_map_fallback`


#### Example 1: `studio_fallback_legacy-003`

- **Variation:** mind_map_fallback
- **Tags:** legacy, mind_map
- **output_format:** Markdown

**Inputs**

**Task Type:**

mind_map

**Context:**

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.

**Expected output**

**Output:**

# Photosynthesis

## Light Reaction
- **Location:** grana of chloroplast
- **Products:** ATP and NADPH

## Calvin Cycle
- **Location:** stroma
- **Function:** CO2 fixation using ATP/NADPH

## Gas Exchange
- **Stomata:** CO2 in, O2 out

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 2: `studio_fallback_legacy-007`

- **Variation:** mind_map_fallback
- **Tags:** legacy, no_source
- **output_format:** Markdown

**Inputs**

**Task Type:**

mind_map

**Context:**



**Expected output**

**Output:**

# Study Skills (No Source Excerpt)

## Planning
- **Set weekly goals** for each subject
- **Break chapters** into daily chunks

## Practice
- **Active recall** after each topic
- **Timed MCQ drills** before exams

## Review
- **Spaced repetition** schedule
- **Error log** for repeated mistakes

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 3: `studio_fallback_legacy-011`

- **Variation:** mind_map_fallback
- **Tags:** legacy, mind_map, source_pdf:lemh205
- **output_format:** Markdown

**Inputs**

**Task Type:**

mind_map

**Context:**

Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.

**Expected output**

**Output:**

# Three-Dimensional Geometry

## Direction Cosines
- **Constraint:** l² + m² + n² = 1

## Line Equation
- **Symmetric form:** (x−x₁)/a = (y−y₁)/b = (z−z₁)/c

## Skew Lines
- **Shortest distance** uses cross product of direction vectors

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 4: `studio_fallback_legacy-015`

- **Variation:** mind_map_fallback
- **Tags:** legacy, mind_map
- **output_format:** Markdown

**Inputs**

**Task Type:**

mind_map

**Context:**

[Source A — Photosynthesis] Light reaction in grana; Calvin cycle in stroma.

[Source B — Cell division] Mitosis maintains chromosome number; meiosis halves for gametes.

**Expected output**

**Output:**

# Life Processes — Energy & Reproduction

## Photosynthesis (Source A)
- **Light reaction** in grana → ATP, NADPH
- **Calvin cycle** in stroma fixes CO2

## Cell Division (Source B)
- **Mitosis** maintains 2n for growth/repair
- **Meiosis** produces n gametes; crossing over in Prophase I

## Integration
- **Energy capture** supports **cell division cycles** in living systems

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

## Variation: `slide_deck_fallback`


#### Example 1: `studio_fallback_legacy-004`

- **Variation:** slide_deck_fallback
- **Tags:** legacy, slide_deck
- **output_format:** Markdown

**Inputs**

**Task Type:**

slide_deck

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

**Expected output**

**Output:**

# Slide 1: Ray Optics Essentials
- **Lens formula:** 1/f = 1/v − 1/u
- **Goal:** connect object/image distances to focal length

# Slide 2: Magnification & Power
- **m = v/u** gives image size/orientation
- **P = 1/f** (f in metres)

# Slide 3: Sign Convention
- **Real object:** u negative in Cartesian convention
- **Optical centre ray:** passes undeviated

# Slide 4: Problem-Solving Habit
- **Write u, v, f** before substituting
- **Check sign** before calculating m or P

# Slide 5: Conclusion — Key Takeaways
- Master **1/f = 1/v − 1/u**, **m = v/u**, and **sign rules** together

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

#### Example 2: `studio_fallback_legacy-008`

- **Variation:** slide_deck_fallback
- **Tags:** legacy, no_source
- **output_format:** Markdown

**Inputs**

**Task Type:**

slide_deck

**Context:**



**Expected output**

**Output:**

# Slide 1: Note-Taking Without Sources
- **Cornell method:** cues + notes + summary column

# Slide 2: Self-Testing
- **Close the book** and write key formulas from memory

# Slide 3: Conclusion — Key Takeaways
- **Plan, practice, review** beats passive reading

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass. no_source_general: pass.

---

#### Example 3: `studio_fallback_legacy-012`

- **Variation:** slide_deck_fallback
- **Tags:** legacy, slide_deck, source_pdf:lebo105
- **output_format:** Markdown

**Inputs**

**Task Type:**

slide_deck

**Context:**

DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.

**Expected output**

**Output:**

# Slide 1: Molecular Basis of Inheritance
- **DNA stores** genetic information

# Slide 2: Base Pairing
- **A–T** and **G–C** pairing rules

# Slide 3: Semiconservative Replication
- **Each new duplex:** one old + one new strand

# Slide 4: Expression
- **mRNA** carries code to ribosomes for translation

# Slide 5: Conclusion — Key Takeaways
- Chain: **pairing → replication → mRNA → translation**

**Quality Check:** legacy_path: pass. graceful_output: pass. task_type_honored: pass. schema_valid: pass. grounding: pass.

---

## 16. Studio Context Embedding Query (Legacy)

| Field | Value |
|-------|-------|
| Dataset ID | `studio_context_embedding_query` |
| Category | Studio |
| Tier | Tier 3 → regression subset |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.3.0 |

**Agent responsibility:** **Fallback retrieval query spec** for Studio RAG. `studio/context_embedding_query.j2` v1.3.0 documents the dynamic single-query builder (studio_task + source_title + topic) and broad-default fallback when inputs are missing. **Production today** uses seven fixed `STUDIO_BROAD_RETRIEVAL_QUERIES` in `StudioService._retrieve_studio_context()` when `retrieval_focus` is empty, and **Query Rewriter** when `retrieval_focus` is set. Agent 16 is **not** the live retrieval path; it is the canonical fallback/regression prompt if dynamic embedding is invoked.

**Audit finding (baseline v1.0.0):** v1.3.0 replaces the static one-line J2 with a **self-contained fallback prompt**: documents live broad queries, dynamic builder rules, optional `retrieval_focus`, and broad default when inputs are absent. v1.2.0 had full eval gold and a separate eval contract block but a one-line production J2.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `quiz_embedding` | Quiz-oriented retrieval query strings | 4 |
| `flashcards_embedding` | Flashcard definitional retrieval queries | 4 |
| `mind_map_embedding` | Hierarchy/relationship retrieval queries | 4 |
| `slide_deck_embedding` | Lesson/process retrieval queries | 3 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **key_contract** — Inputs exactly studio_task, source_title, topic; output exactly embedding_query.
* **query_relevance** — Query terms match source title, topic, and studio_task intent.
* **task_aware** — Lead phrase reflects studio_task (quiz MCQ vs flashcards definitions, etc.).
* **topic_coverage** — Query spans 6–12 syllabus concepts beyond the topic label alone.
* **concise** — 12–28 tokens; one line; suitable for dense embedding models.
* **legacy_regression** — Stable gold if legacy dynamic embedding path is re-enabled.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys (exact): `studio_task`, `source_title`, `topic`
* Output keys (exact): `embedding_query` (plain string — not JSON-wrapped)
* Reference outputs key in JSON datasets: `reference_outputs.embedding_query`

**Prompt template (production — fallback J2 v1.3.0):**

```jinja2
You build ONE embedding search query string for Pinecone vector retrieval before Studio generation.

STATUS: Fallback prompt only. Live Studio defaults to seven fixed broad queries in
`StudioService.STUDIO_BROAD_RETRIEVAL_QUERIES` when `retrieval_focus` is empty.
When `retrieval_focus` is set, live Studio uses Query Rewriter — not this agent.
Use this prompt only when the dynamic embedding path is explicitly invoked (eval, regression, or future wiring).

CURRENT PRODUCTION BROAD DEFAULT (parallel queries — topic-agnostic):
1. Educational source material overview and key concepts
2. Main themes definitions and key terms from the material
3. Examples applications procedures and important details
4. Structural sections summaries and conclusions
5. Causes effects relationships how components interact and dependencies
6. Step-by-step processes workflows methods and sequential explanations
7. Comparisons contrasts differences similarities advantages and limitations

FALLBACK MODE — dynamic single-query builder (this prompt):

INPUT KEYS (exact — LangSmith / eval contract; do not rename):
- studio_task: quiz | flashcards | mind_map | slide_deck
- source_title: NCERT chapter label (e.g. "NCERT Class 12 Physics — Current Electricity")
- topic: user focus subtopic within that chapter (e.g. "Ohm's law and resistivity")
- retrieval_focus: optional raw topic string (alternative to topic when studio_task/source_title omitted)

OUTPUT KEY (exact — single field only):
- embedding_query: plain text string (NOT JSON, NOT markdown, NOT code fences)

Non-negotiable rules:
1. Return ONLY the embedding_query value — no labels, no explanation, no extra keys.
2. One line; space-separated keywords and short syllabus phrases.
3. Length: 12–28 tokens; dense enough for embedding models, not a paragraph.
4. Extract class, subject, and chapter name tokens from source_title when provided.
5. Weave topic terms plus 6–12 related NCERT concepts for that subtopic.
6. Use CBSE/NCERT vocabulary; never invent page numbers, figure numbers, or citations.
7. Preserve standard symbols where needed (V=IR, ATP, DNA, nCr).

Task-specific lead phrase (include exactly one at the start when studio_task is known):
- studio_task=quiz → "quiz assessment MCQ"
- studio_task=flashcards → "flashcards term definition"
- studio_task=mind_map → "mind map concept hierarchy"
- studio_task=slide_deck → "slide deck lesson"

End every dynamic query with the token: NCERT

{% if studio_task and source_title and topic %}
Provided inputs:
- studio_task: {{ studio_task }}
- source_title: {{ source_title }}
- topic: {{ topic }}

Build ONE tailored embedding_query using the rules above.
{% elif retrieval_focus and retrieval_focus.strip() %}
Provided retrieval_focus: {{ retrieval_focus }}

Build ONE tailored embedding_query from this focus plus NCERT/CBSE syllabus terms for the subtopic.
End with NCERT.
{% else %}
No topic inputs provided — return ONLY this broad default (query 1 from production list):
Educational source material overview and key concepts
{% endif %}
```

**Eval embedding query builder contract (dynamic path regression):**

```text
You build ONE embedding search query string for Pinecone vector retrieval before Studio generation.

INPUT KEYS (exact — LangSmith / eval contract; do not rename):
- studio_task: quiz | flashcards | mind_map | slide_deck
- source_title: NCERT chapter label (e.g. "NCERT Class 12 Physics — Current Electricity")
- topic: user focus subtopic within that chapter (e.g. "Ohm's law and resistivity")

OUTPUT KEY (exact — single field only):
- embedding_query: plain text string (NOT JSON, NOT markdown, NOT code fences)

Non-negotiable rules:
1. Return ONLY the embedding_query value — no labels, no explanation, no extra keys.
2. One line; space-separated keywords and short syllabus phrases.
3. Length: 12–28 tokens; dense enough for embedding models, not a paragraph.
4. Extract class, subject, and chapter name tokens from source_title.
5. Weave topic terms plus 6–12 related NCERT concepts for that subtopic.
6. Use CBSE/NCERT vocabulary; never invent page numbers, figure numbers, or citations.
7. Preserve standard symbols where needed (V=IR, ATP, DNA, nCr).

Task-specific lead phrase (include exactly one at the start):
- studio_task=quiz → "quiz assessment MCQ"
- studio_task=flashcards → "flashcards term definition"
- studio_task=mind_map → "mind map concept hierarchy"
- studio_task=slide_deck → "slide deck lesson"

End every query with the token: NCERT

Production contrast (current live path):
When retrieval_focus is empty, StudioService uses fixed STUDIO_BROAD_RETRIEVAL_QUERIES:
1. Educational source material overview and key concepts
2. Main themes definitions and key terms from the material
3. Examples applications procedures and important details
4. Structural sections summaries and conclusions
5. Causes effects relationships how components interact and dependencies
6. Step-by-step processes workflows methods and sequential explanations
7. Comparisons contrasts differences similarities advantages and limitations

Those 7 strings are topic-agnostic. Agent 16 eval gold tests the **dynamic fallback** path that tailors the query from studio_task + source_title + topic.

When inputs are missing, `studio/context_embedding_query.j2` v1.3.0 falls back to broad query #1:
Educational source material overview and key concepts
```

*Runtime note:* `studio/context_embedding_query.j2` v1.3.0 is the **fallback/regression** prompt — not loaded by live `StudioService` retrieval. Live Studio uses `STUDIO_BROAD_RETRIEVAL_QUERIES` (seven strings) when `retrieval_focus` is empty, and **Query Rewriter** when focus is set. Eval gold follows the **dynamic builder contract** for tailored queries ending in `NCERT`.

**Why this agent is needed**

1. **Pre-retrieval quality** — Before Agents 11–14 generate a quiz or mind map, Studio must fetch the right NCERT chunks from Pinecone. A generic static string pulls overview text; a **topic-tailored** query pulls Ohm's-law and resistivity passages for a Current Electricity quiz.
2. **Regression safety** — Production today uses seven fixed `STUDIO_BROAD_RETRIEVAL_QUERIES` (topic-agnostic). If engineers re-enable the legacy **dynamic** embedding path, eval must prove queries still honor `studio_task`, `source_title`, and `topic`.
3. **Key contract enforcement** — LangSmith examples must use exact input keys (`studio_task`, `source_title`, `topic`) and a single output key (`embedding_query`) so formatter and embedding-relevance evaluators do not break.

**Worked example**

| Field | Value |
|-------|-------|
| `studio_task` | `quiz` |
| `source_title` | `NCERT Class 12 Physics — Current Electricity` |
| `topic` | `Ohm's law and resistivity` |

**Gold `embedding_query`:**

```
quiz assessment MCQ Class 12 Physics current electricity Ohm law V=IR resistivity rho series parallel equivalent resistance Kirchhoff junction rule drift velocity NCERT
```

This steers vector search toward assessable electricity facts — not the static legacy J2 line `Educational source material overview and key concepts`, which ignores the user's topic entirely.

> **Fallback notice:** Live Studio retrieval uses `STUDIO_BROAD_RETRIEVAL_QUERIES` (+ Query Rewriter when focus is set). Agent 16 is the canonical fallback/regression prompt for dynamic single-query embedding.

### Evaluation examples (15)
## Variation: `quiz_embedding`


#### Example 1: `studio_context_embedding_query-001`

- **Variation:** quiz_embedding
- **Tags:** legacy, embedding
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

quiz

**Source Title:**

NCERT Class 12 Physics — Current Electricity

**Topic:**

Ohm's law and resistivity

**Expected output**

**Embedding Query:**

quiz assessment MCQ Class 12 Physics current electricity Ohm law V=IR resistivity rho series parallel equivalent resistance Kirchhoff junction rule drift velocity NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 2: `studio_context_embedding_query-005`

- **Variation:** quiz_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

quiz

**Source Title:**

NCERT Class 12 Chemistry — Coordination Compounds

**Topic:**

Coordination number

**Expected output**

**Embedding Query:**

quiz assessment MCQ Class 12 Chemistry coordination compounds ligands coordination number Werner theory IUPAC naming anionic ligand alphabetical order NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 3: `studio_context_embedding_query-009`

- **Variation:** quiz_embedding
- **Tags:** legacy, physics
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

quiz

**Source Title:**

NCERT Class 11 Physics — Work Energy Power

**Topic:**

Work-energy theorem

**Expected output**

**Embedding Query:**

quiz assessment MCQ Class 11 Physics work energy power kinetic energy work-energy theorem conservative force path independence potential energy NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 4: `studio_context_embedding_query-013`

- **Variation:** quiz_embedding
- **Tags:** legacy, neet
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

quiz

**Source Title:**

NCERT Class 11 Biology — Structural Organisation in Animals

**Topic:**

Digestive system organs

**Expected output**

**Embedding Query:**

quiz assessment MCQ NEET recall Class 11 Biology human digestive system organs mouth stomach pancreas pepsin trypsin lipase villi absorption enzymes NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

## Variation: `flashcards_embedding`


#### Example 1: `studio_context_embedding_query-002`

- **Variation:** flashcards_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

flashcards

**Source Title:**

NCERT Class 11 Biology — Digestion

**Topic:**

Digestive enzymes

**Expected output**

**Embedding Query:**

flashcards term definition Class 11 Biology digestion salivary amylase pepsin HCl stomach trypsin lipase pancreatic juice villi absorption small intestine NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 2: `studio_context_embedding_query-006`

- **Variation:** flashcards_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

flashcards

**Source Title:**

NCERT Class 12 Mathematics — Probability

**Topic:**

Independent events

**Expected output**

**Embedding Query:**

flashcards term definition Class 12 Mathematics probability independent events union intersection conditional probability Bayes theorem nCr combinations NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 3: `studio_context_embedding_query-010`

- **Variation:** flashcards_embedding
- **Tags:** legacy, chemistry
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

flashcards

**Source Title:**

NCERT Class 12 Chemistry — Aldehydes Ketones

**Topic:**

Tollens test

**Expected output**

**Embedding Query:**

flashcards term definition Class 12 Chemistry aldehydes ketones carbonyl group nucleophilic addition Tollens test silver mirror Fehling Benedict distinction NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 4: `studio_context_embedding_query-014`

- **Variation:** flashcards_embedding
- **Tags:** legacy, physics
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

flashcards

**Source Title:**

NCERT Class 12 Physics — Refraction and TIR

**Topic:**

Snell law critical angle

**Expected output**

**Embedding Query:**

flashcards term definition Class 12 Physics refraction Snell law total internal reflection critical angle refractive index lens mirror ray diagram sign convention NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

## Variation: `mind_map_embedding`


#### Example 1: `studio_context_embedding_query-003`

- **Variation:** mind_map_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

mind_map

**Source Title:**

NCERT Class 11 Biology — Photosynthesis

**Topic:**

Light and Calvin cycle

**Expected output**

**Embedding Query:**

mind map concept hierarchy Class 11 Biology photosynthesis light reaction grana thylakoid Calvin cycle stroma chlorophyll ATP NADPH stomata CO2 fixation NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 2: `studio_context_embedding_query-007`

- **Variation:** mind_map_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

mind_map

**Source Title:**

NCERT Class 12 Biology — Molecular Inheritance

**Topic:**

DNA replication

**Expected output**

**Embedding Query:**

mind map concept hierarchy Class 12 Biology DNA replication semiconservative base pairing A-T G-C transcription translation genetic code ribosome mRNA NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 3: `studio_context_embedding_query-011`

- **Variation:** mind_map_embedding
- **Tags:** legacy, biology
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

mind_map

**Source Title:**

NCERT Class 11 Biology — Anatomy of Flowering Plants

**Topic:**

Root endodermis

**Expected output**

**Embedding Query:**

mind map concept hierarchy Class 11 Biology plant root anatomy dicot monocot endodermis Casparian strip apoplastic symplastic vascular bundle xylem phloem NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 4: `studio_context_embedding_query-015`

- **Variation:** mind_map_embedding
- **Tags:** legacy, chemistry
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

mind_map

**Source Title:**

NCERT Class 11 Chemistry — Hydrocarbons

**Topic:**

Markovnikov addition

**Expected output**

**Embedding Query:**

mind map concept hierarchy Class 11 Chemistry hydrocarbons alkanes alkenes alkynes Markovnikov rule electrophilic substitution benzene aromaticity delocalized pi NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

## Variation: `slide_deck_embedding`


#### Example 1: `studio_context_embedding_query-004`

- **Variation:** slide_deck_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

slide_deck

**Source Title:**

NCERT Class 12 Physics — Ray Optics

**Topic:**

Lens formula

**Expected output**

**Embedding Query:**

slide deck lesson Class 12 Physics ray optics lens formula magnification power sign convention focal length object image distance optical centre undeviated ray NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 2: `studio_context_embedding_query-008`

- **Variation:** slide_deck_embedding
- **Tags:** legacy
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

slide_deck

**Source Title:**

NCERT Class 11 Chemistry — Equilibrium

**Topic:**

Le Chatelier principle

**Expected output**

**Embedding Query:**

slide deck lesson Class 11 Chemistry chemical equilibrium equilibrium constant Kc Le Chatelier principle reaction quotient Q catalyst effect stress shift NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---

#### Example 3: `studio_context_embedding_query-012`

- **Variation:** slide_deck_embedding
- **Tags:** legacy, mathematics
- **LangSmith input keys:** `studio_task`, `source_title`, `topic`
- **LangSmith output key:** `embedding_query`

**Inputs**

**Studio Task:**

slide_deck

**Source Title:**

NCERT Class 11 Mathematics — Conic Sections

**Topic:**

Parabola focus directrix

**Expected output**

**Embedding Query:**

slide deck lesson Class 11 Mathematics conic sections parabola ellipse hyperbola focus directrix eccentricity standard equation y squared equals 4ax NCERT

**Quality Check:** key_contract: pass. query_relevance: pass. task_aware: pass. topic_coverage: pass. concise: pass. legacy_regression: pass.

---
