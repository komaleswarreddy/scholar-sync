## 10. Studio System Prompt (JSON tasks)

| Field | Value |
|-------|-------|
| Dataset ID | `studio_system_json` |
| Category | Studio |
| Tier | Tier 3 baseline → focused enrichment set |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.1.0 |

**Agent responsibility:** Shared **system prompt** (`studio/system_educational_json_markdown.j2`) prepended to all structured Studio tasks (quiz, flashcards, mind map, slide deck). Enforces **format discipline** — JSON-only when the task requests JSON, Markdown-only when the task requests Markdown. Does **not** generate pedagogical content alone; the paired **user/task template** supplies the task.

**Audit finding (baseline v1.0.0):** The original 10-example set reused one task instruction across mismatched gold shapes (object vs array), abbreviated the system prompt to four bullet lines, and did not document the system-only eval role. Expanded to 15 examples with locked variation buckets, full inline production system prompt, and explicit format-discipline gold for array, object, markdown, empty, and thin-source cases.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `json_array` | Array of term/definition or formula objects | 4 |
| `json_object` | Nested object schema | 3 |
| `markdown_only` | No JSON fences | 3 |
| `empty_context` | Refusal / `[]` — no fabrication | 2 |
| `thin_source` | Minimum viable output from thin excerpt | 2 |
| `json_numeric_object` | Numeric/conic facts object | 1 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **valid_json** — Output parses as JSON when task requests JSON; no trailing prose.
* **format_discipline** — Markdown-only tasks return no JSON; JSON tasks return no markdown fences.
* **schema_match** — Object vs array shape matches task_instruction keys and counts.
* **grounding** — Facts appear in context excerpt; no invented numbers or terms.
* **no_fences** — No ``` markdown code fences wrapping JSON output.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `context`, `task_instruction`
* Output keys: `json_output` (JSON tasks) or `markdown_output` (Markdown tasks)

**Prompt template (system — production):**

```jinja2
You are an expert educational content generator for school learners.

Rules:
- When Source content is provided, ground all substantive facts in that excerpt only.
- Do not invent facts, names, or numbers not supported by the excerpt.
- For JSON tasks: return valid JSON only — no markdown fences, no extra text.
- For Markdown tasks: return clean Markdown only — no code fences, no preamble or postscript.
- Be accurate, concise, and learner-friendly.
- Think step-by-step internally; do not reveal chain-of-thought.
```

*Runtime note:* Paired as **system** prompt in [`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) `StudioService._generate_structured_task()`. Agent 10 evals system format discipline **in isolation**; task templates are Agents 11–14.

### Evaluation examples (15)
## Variation: `json_array`


#### Example 1: `studio_system_json-001`

- **Variation:** json_array
- **Tags:** cbse, physics, source_pdf:leph103
- **source_pdf:** leph103.pdf

**Inputs**

**Context:**

Ohm's law: V = IR. Resistivity ρ = RA/l. Series: R_eq = R1+R2. Parallel: 1/R_eq = 1/R1+1/R2. Kirchhoff's junction rule: sum of currents into a node equals sum leaving.

**Task Instruction:**

Return a JSON array of exactly 3 objects, each with keys term and definition, using only the excerpt.

**Expected output**

**Json Output:**

[
  {
    "term": "Ohm's law",
    "definition": "Potential difference V equals current I times resistance R (V = IR)."
  },
  {
    "term": "Resistivity",
    "definition": "Material property ρ related to resistance by ρ = RA/l."
  },
  {
    "term": "Kirchhoff's junction rule",
    "definition": "Sum of currents entering a junction equals sum leaving."
  }
]

**Quality Check:** valid_json: pass. schema_match: pass. grounding: pass. no_fences: pass.

---

#### Example 2: `studio_system_json-005`

- **Variation:** json_array
- **Tags:** cbse, physics, source_pdf:keph105
- **source_pdf:** keph105.pdf

**Inputs**

**Context:**

Work W = F·s cos θ. Kinetic energy K = ½mv². Power P = W/t. Work-energy theorem: net work equals change in kinetic energy.

**Task Instruction:**

Return a JSON array of 4 objects with keys formula and quantity extracted from the excerpt.

**Expected output**

**Json Output:**

[
  {
    "formula": "W = F·s cos θ",
    "quantity": "Work"
  },
  {
    "formula": "K = ½mv²",
    "quantity": "Kinetic energy"
  },
  {
    "formula": "P = W/t",
    "quantity": "Power"
  },
  {
    "formula": "W_net = ΔK",
    "quantity": "Work-energy theorem"
  }
]

**Quality Check:** count_match: pass. grounding: pass.

---

#### Example 3: `studio_system_json-006`

- **Variation:** json_array
- **Tags:** cbse, chemistry, source_pdf:lech105
- **source_pdf:** lech105.pdf

**Inputs**

**Context:**

Coordination entity: central metal ion + ligands. Coordination number = number of σ-donor atoms bonded to metal. IUPAC: ligands named alphabetically; anionic ligands end in -o.

**Task Instruction:**

Output JSON array of 3 {term, definition} pairs — valid JSON only, no markdown.

**Expected output**

**Json Output:**

[
  {
    "term": "Coordination entity",
    "definition": "Central metal ion bonded to ligands in a complex."
  },
  {
    "term": "Coordination number",
    "definition": "Count of σ-donor atoms directly bonded to the metal."
  },
  {
    "term": "IUPAC ligand naming",
    "definition": "Ligands listed alphabetically; anionic ligands take -o suffix."
  }
]

**Quality Check:** grounding: pass. valid_json: pass.

---

#### Example 4: `studio_system_json-008`

- **Variation:** json_array
- **Tags:** neet, biology, source_pdf:lebo105
- **source_pdf:** lebo105.pdf

**Inputs**

**Context:**

DNA double helix: antiparallel strands, A pairs T, G pairs C. Replication is semiconservative. mRNA carries genetic code to ribosomes for translation.

**Task Instruction:**

JSON array of exactly 3 term/definition objects from excerpt. JSON only.

**Expected output**

**Json Output:**

[
  {
    "term": "Base pairing",
    "definition": "Adenine with thymine; guanine with cytosine in DNA."
  },
  {
    "term": "Semiconservative replication",
    "definition": "Each new DNA duplex has one old and one new strand."
  },
  {
    "term": "Translation",
    "definition": "Ribosomes synthesize protein using mRNA template."
  }
]

**Quality Check:** grounding: pass. count_match: pass.

---

#### Example 5: `studio_system_json-011`

- **Variation:** json_array
- **Tags:** cbse, chemistry, source_pdf:lech103
- **source_pdf:** lech103.pdf

**Inputs**

**Context:**

Electrolysis of molten NaCl: Na+ migrates to cathode, Cl− to anode. Faraday's first law: mass deposited proportional to charge passed.

**Task Instruction:**

Return JSON array of step objects with step (number) and event or rule (string). Exactly 3 items. JSON only.

**Expected output**

**Json Output:**

[
  {
    "step": 1,
    "event": "Na+ ions move to cathode"
  },
  {
    "step": 2,
    "event": "Cl− ions move to anode"
  },
  {
    "step": 3,
    "rule": "Faraday's first law — mass ∝ charge"
  }
]

**Quality Check:** valid_json: pass. grounding: pass.

---

## Variation: `json_object`


#### Example 1: `studio_system_json-002`

- **Variation:** json_object
- **Tags:** cbse, biology, source_pdf:kebo110
- **source_pdf:** kebo110.pdf

**Inputs**

**Context:**

Photosynthesis: light reaction in grana produces ATP and NADPH; Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata allow gas exchange.

**Task Instruction:**

Return a JSON object with keys process, stages (array of objects with name, location, and products or function), and key_structures (array of strings). Excerpt only.

**Expected output**

**Json Output:**

{
  "process": "Photosynthesis",
  "stages": [
    {
      "name": "Light reaction",
      "location": "grana",
      "products": [
        "ATP",
        "NADPH"
      ]
    },
    {
      "name": "Calvin cycle",
      "location": "stroma",
      "function": "CO2 fixation"
    }
  ],
  "key_structures": [
    "chlorophyll",
    "stomata"
  ]
}

**Quality Check:** valid_json: pass. nested_schema: pass. grounding: pass.

---

#### Example 2: `studio_system_json-007`

- **Variation:** json_object
- **Tags:** cbse, mathematics, source_pdf:lemh207
- **source_pdf:** lemh207.pdf

**Inputs**

**Context:**

P(E) = favourable outcomes / total outcomes. P(A∪B) = P(A)+P(B)−P(A∩B). For independent events P(A∩B) = P(A)P(B).

**Task Instruction:**

Return one JSON object with topic (string) and rules (array of {rule, expression}). No extra text.

**Expected output**

**Json Output:**

{
  "topic": "Probability axioms",
  "rules": [
    {
      "rule": "Classical probability",
      "expression": "P(E) = n(E)/n(S)"
    },
    {
      "rule": "Addition theorem",
      "expression": "P(A∪B) = P(A)+P(B)−P(A∩B)"
    },
    {
      "rule": "Independent events",
      "expression": "P(A∩B) = P(A)P(B)"
    }
  ]
}

**Quality Check:** schema_match: pass. grounding: pass.

---

## Variation: `markdown_only`


#### Example 1: `studio_system_json-003`

- **Variation:** markdown_only
- **Tags:** cbse, physics, source_pdf:leph201
- **source_pdf:** leph201.pdf

**Inputs**

**Context:**

Lens formula: 1/f = 1/v - 1/u. Sign convention: distances measured from optical centre; u negative for real object.

**Task Instruction:**

Return Markdown only (no JSON). Use a ## heading and bullet list summarizing the lens formula and sign convention from the excerpt.

**Expected output**

**Markdown Output:**

## Lens formula (sign convention)

- **Formula:** 1/f = 1/v − 1/u
- **Origin:** Measure distances from the optical centre
- **Real object:** Object distance u is taken as negative

**Quality Check:** markdown_only: pass. no_json: pass. grounding: pass.

---

#### Example 2: `studio_system_json-009`

- **Variation:** markdown_only
- **Tags:** cbse, chemistry, source_pdf:lech103
- **source_pdf:** lech103.pdf

**Inputs**

**Context:**

Galvanic cell: anode oxidation, cathode reduction. EMF E°cell = E°cathode − E°anode. Nernst equation relates EMF to concentration.

**Task Instruction:**

Produce Markdown summary with ## heading and bullets. Do NOT return JSON.

**Expected output**

**Markdown Output:**

## Galvanic cell essentials

- **Anode:** site of oxidation
- **Cathode:** site of reduction
- **Standard EMF:** E°cell = E°cathode − E°anode
- **Nernst equation:** links cell EMF to ion concentrations

**Quality Check:** format_discipline: pass. grounding: pass.

---

#### Example 3: `studio_system_json-012`

- **Variation:** markdown_only
- **Tags:** neet, biology, source_pdf:kebo110
- **source_pdf:** kebo110.pdf

**Inputs**

**Context:**

Mitosis: one division, 2n→2n, growth/repair. Meiosis: two divisions, 2n→n, gamete formation; crossing over in Prophase I.

**Task Instruction:**

Return Markdown only: ## heading plus a comparison table of mitosis vs meiosis from excerpt. No JSON.

**Expected output**

**Markdown Output:**

## Mitosis vs Meiosis

| Feature | Mitosis | Meiosis |
|---------|---------|--------|
| Divisions | One | Two |
| Chromosome number | Maintained (2n) | Halved (n) |
| Purpose | Growth/repair | Gametes |
| Crossing over | Not typical | Prophase I |

**Quality Check:** markdown_only: pass. grounding: pass.

---

## Variation: `empty_context`


#### Example 1: `studio_system_json-004`

- **Variation:** empty_context
- **Tags:** edge_case, no_source

**Inputs**

**Context:**



**Task Instruction:**

Return a JSON array of key terms with definitions from the excerpt.

**Expected output**

**Json Output:**

[]

**Quality Check:** empty_context: pass. no_hallucination: pass. valid_json: pass.

---

#### Example 2: `studio_system_json-014`

- **Variation:** empty_context
- **Tags:** edge_case, no_source

**Inputs**

**Context:**

   

**Task Instruction:**

Return Markdown summary of key concepts from the excerpt.

**Expected output**

**Markdown Output:**

## Insufficient source

- No indexed excerpt available; cannot summarize without evidence.

**Quality Check:** empty_context: pass. no_hallucination: pass.

---

## Variation: `thin_source`


#### Example 1: `studio_system_json-010`

- **Variation:** thin_source
- **Tags:** cbse, mathematics, source_pdf:kemh107
- **source_pdf:** kemh107.pdf

**Inputs**

**Context:**

Binomial theorem: (a+b)^n expansion uses nCr coefficients.

**Task Instruction:**

Return JSON array with as many term/definition pairs as the thin excerpt supports (minimum 1). JSON only.

**Expected output**

**Json Output:**

[
  {
    "term": "Binomial coefficient",
    "definition": "nCr counts combinations in (a+b)^n expansion."
  }
]

**Quality Check:** thin_source_handling: pass. valid_json: pass.

---

#### Example 2: `studio_system_json-013`

- **Variation:** thin_source
- **Tags:** cbse, biology, source_pdf:kebo106
- **source_pdf:** kebo106.pdf

**Inputs**

**Context:**

Casparian strip in endodermis has suberin. It blocks apoplastic flow forcing symplastic uptake into stele.

**Task Instruction:**

JSON array of 3 {question, answer} pairs grounded in excerpt. No markdown fences.

**Expected output**

**Json Output:**

[
  {
    "question": "Where is the Casparian strip?",
    "answer": "In the endodermis of roots."
  },
  {
    "question": "What does suberin do?",
    "answer": "Blocks apoplastic flow at the endodermis."
  },
  {
    "question": "Why does it matter?",
    "answer": "Forces selective symplastic uptake into stele."
  }
]

**Quality Check:** valid_json: pass. grounding: pass.

---

## Variation: `json_numeric_object`


#### Example 1: `studio_system_json-015`

- **Variation:** json_numeric_object
- **Tags:** cbse, mathematics, source_pdf:kemh111
- **source_pdf:** kemh111.pdf

**Inputs**

**Context:**

For y²=4ax parabola: focus at (a,0), directrix x=−a, eccentricity e=1. Latus rectum length 4a.

**Task Instruction:**

Return one JSON object with keys conic, standard_form, focus, directrix, eccentricity, latus_rectum. Valid JSON only.

**Expected output**

**Json Output:**

{
  "conic": "parabola",
  "standard_form": "y²=4ax",
  "focus": "(a, 0)",
  "directrix": "x = -a",
  "eccentricity": 1,
  "latus_rectum": "4a"
}

**Quality Check:** schema_match: pass. grounding: pass.

---
