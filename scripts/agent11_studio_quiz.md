## 11. Studio Quiz Generator

| Field | Value |
|-------|-------|
| Dataset ID | `studio_quiz` |
| Category | Studio |
| Tier | Tier 2 |
| Target examples | 25 |
| Actual examples | 25 |
| Version | 1.1.0 |

**Agent responsibility:** Generate a JSON quiz `{title, questions[]}` from retrieved source excerpts. Custom instructions override default question count (5–7) and difficulty. Production pairs system prompt + [`studio/quiz_prompt.j2`](packages/core/prompts/templates/studio/quiz_prompt.j2).

**Audit finding (baseline v1.0.0):** The original dataset had question-count mismatches vs custom_instructions, placeholder MCQs, and no scope coverage matrix. Rebuilt with 25 examples spanning all scope modes, locked variation taxonomy, full inline system + task prompts, and gold quizzes honoring requested counts and difficulty.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `per_concept` | Topic-focused custom instructions | 5 |
| `multi_concept` | Full-breadth / all topics in context | 4 |
| `per_source` | Single-source excerpt | 5 |
| `multi_source` | Merged multi-doc context + synthesis | 5 |
| `no_source` | Empty context → failure/generic branch | 2 |
| `custom_override` | Count/difficulty/slide/language overrides | 4 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **question_count_match** — Question count matches custom_instructions (e.g. '5 MCQs' → 5 questions).
* **schema_valid** — Valid JSON; correct_answer ∈ options; 2–4 options per question.
* **options_quality** — Four options when material supports; no duplicate distractors.
* **difficulty_compliance** — Easy/medium/hard vocabulary and reasoning depth per instructions.
* **grounding** — Questions and explanations grounded in context excerpt only.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `context`, `custom_instructions`
* Output keys: `quiz_json`
* Production also uses: `retrieval_queries_note` (not in LangSmith eval keys)

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

**Prompt template (user/task — production):**

```jinja2
You are an **expert quiz author** for Class 11–12 classroom self-assessment. Create a high-quality quiz from the provided material.

**Selected sources:** {{ selected_source_count }} document(s).

## Source scope (mandatory)
- Use **only** the Source content excerpt below.
- Questions, options, and explanations must be supported by the excerpt.
{% if selected_source_count | int > 1 %}
- Distribute questions across the retrieved material so all represented sources contribute when the excerpt includes them.
{% endif %}

Output requirements (strict):
- Return ONLY one valid JSON object.
- Do NOT use markdown, code fences, comments, or extra text.
- Use exactly this schema:
{
  "title": "Short quiz title",
  "questions": [
    {
      "question": "Clear question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "One option string that exactly matches an item in options",
      "explanation": "1-2 sentence reason"
    }
  ]
}

Question count:
{% if custom_instructions and custom_instructions.strip() %}
- Follow the question count range and difficulty given in **Additional user instructions** below. Those instructions override any default below.
{% else %}
- Generate between **5 and 7** questions (inclusive) unless the source material is too thin; then use as many solid questions as the material supports (minimum 3 if possible).
{% endif %}

Quality requirements:
- Each question must have exactly 4 options.
- Questions should test understanding, not only memorization.
- Keep wording unambiguous and learner-friendly.
- Avoid duplicate questions or near-duplicate options.
- Keep explanations concise and accurate to the source.

Compliance (when custom instructions are present):
- Honor the requested difficulty (easy / medium / hard): adjust reasoning depth, distractor quality, and vocabulary accordingly.
- If instructions ask for a **topic focus**, most questions must clearly relate to that focus while staying grounded in the source.
- If instructions say **no narrow topic** / **full breadth** / **all selected sources**, distribute questions across the retrieved material so the quiz reflects the whole context, not one subsection.

{% if retrieval_queries_note and retrieval_queries_note.strip() %}
Retrieval queries used for vector search (ground the quiz in material retrieved with these queries):
{{ retrieval_queries_note }}

{% endif %}
{% if context and context.strip() %}
Source content:
{{ context }}
{% else %}
No source content was provided. Return exactly:
{"title": "Insufficient source text", "questions": []}
Do not invent questions from general knowledge.
{% endif %}

{% if custom_instructions %}
Additional user instructions:
{{ custom_instructions }}
{% endif %}
```

*Runtime note:* [`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) `StudioService._generate_structured_task()` plus [`packages/core/validation/studio_output_validators.py`](packages/core/validation/studio_output_validators.py) `validate_quiz_schema()`.

**Scope coverage**

| scope_mode | Min examples | This dataset |
|------------|--------------|--------------|
| per_concept | 4 | 5 |
| multi_concept | 3 | 4 |
| per_source | 4 | 5 |
| multi_source | 5 | 5 |
| no_source | 2 | 2 |
| custom_override | — | 4 (distributed) |

### Evaluation examples (25)
## Variation: `per_concept`


#### Example 1: `studio_quiz-001`

- **Variation:** per_concept
- **Tags:** cbse, physics, scope_mode:per_concept, source_pdf:leph103
- **scope_mode:** per_concept

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

5 MCQs, medium difficulty, focus Ohm's law and series circuits

**Expected output**

**Quiz Json:**

{
  "title": "Current Electricity — Ohm & Series",
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

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-002`

- **Variation:** per_concept
- **Tags:** neet, biology, scope_mode:per_concept, source_pdf:kebo107
- **scope_mode:** per_concept

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Custom Instructions:**

4 MCQs, hard NEET-style, digestive enzymes only

**Expected output**

**Quiz Json:**

{
  "title": "Digestive Enzymes NEET Drill",
  "questions": [
    {
      "question": "Carbohydrate digestion begins in mouth with:",
      "options": [
        "Pepsin",
        "Salivary amylase",
        "Trypsin",
        "Lipase"
      ],
      "correct_answer": "Salivary amylase",
      "explanation": "Salivary amylase acts on starch in mouth."
    },
    {
      "question": "Pepsin requires which stomach condition?",
      "options": [
        "Alkaline pH",
        "Acidic HCl medium",
        "Neutral pH",
        "No enzymes"
      ],
      "correct_answer": "Acidic HCl medium",
      "explanation": "Pepsin works in acidic stomach environment."
    },
    {
      "question": "Trypsin is activated in:",
      "options": [
        "Stomach",
        "Mouth",
        "Duodenum via pancreatic juice",
        "Large intestine"
      ],
      "correct_answer": "Duodenum via pancreatic juice",
      "explanation": "Pancreatic trypsin enters duodenum."
    },
    {
      "question": "Most nutrient absorption occurs in:",
      "options": [
        "Stomach",
        "Oesophagus",
        "Small intestine villi",
        "Mouth"
      ],
      "correct_answer": "Small intestine villi",
      "explanation": "Villi absorb digested nutrients."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 3: `studio_quiz-003`

- **Variation:** per_concept
- **Tags:** cbse, chemistry, scope_mode:per_concept, source_pdf:lech105
- **scope_mode:** per_concept

**Inputs**

**Context:**

Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.

**Custom Instructions:**

3 MCQs, easy, coordination number only

**Expected output**

**Quiz Json:**

{
  "title": "Coordination Number Basics",
  "questions": [
    {
      "question": "Coordination number counts:",
      "options": [
        "Electrons in metal",
        "σ-donor atoms bonded to metal",
        "Ligand mass",
        "Oxidation state only"
      ],
      "correct_answer": "σ-donor atoms bonded to metal",
      "explanation": "CN = donor atoms directly bonded."
    },
    {
      "question": "[Fe(CN)6]4- has coordination number:",
      "options": [
        "4",
        "6",
        "8",
        "2"
      ],
      "correct_answer": "6",
      "explanation": "Six cyanide ligands → CN=6."
    },
    {
      "question": "Coordination entity contains:",
      "options": [
        "Central metal ion + ligands",
        "Only anions",
        "Only cations",
        "Free solvent"
      ],
      "correct_answer": "Central metal ion + ligands",
      "explanation": "Complex = metal + attached ligands."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 4: `studio_quiz-004`

- **Variation:** per_concept
- **Tags:** cbse, mathematics, scope_mode:per_concept, source_pdf:lemh207
- **scope_mode:** per_concept

**Inputs**

**Context:**

P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

**Custom Instructions:**

5 MCQs, medium, independent events focus

**Expected output**

**Quiz Json:**

{
  "title": "Independent Events Quiz",
  "questions": [
    {
      "question": "For independent A and B, P(A∩B) equals:",
      "options": [
        "P(A)+P(B)",
        "P(A)P(B)",
        "P(A)/P(B)",
        "1"
      ],
      "correct_answer": "P(A)P(B)",
      "explanation": "Independence: multiply probabilities."
    },
    {
      "question": "Classical P(E) equals:",
      "options": [
        "favourable/total outcomes",
        "total/favourable",
        "P(A)+P(B)",
        "Always 1/2"
      ],
      "correct_answer": "favourable/total outcomes",
      "explanation": "Laplace definition."
    },
    {
      "question": "P(A∪B) general addition rule:",
      "options": [
        "P(A)+P(B)-P(A∩B)",
        "P(A)P(B)",
        "P(A)-P(B)",
        "P(A)/P(B)"
      ],
      "correct_answer": "P(A)+P(B)-P(A∩B)",
      "explanation": "Inclusion-exclusion."
    },
    {
      "question": "If A and B independent, knowing B occurred:",
      "options": [
        "Changes P(A)",
        "Does not change P(A)",
        "Makes P(A)=0",
        "Makes P(A)=1"
      ],
      "correct_answer": "Does not change P(A)",
      "explanation": "Independence means no influence."
    },
    {
      "question": "Bayes theorem relates:",
      "options": [
        "Prior and likelihood to posterior",
        "Only means",
        "Only variances",
        "Matrix rank"
      ],
      "correct_answer": "Prior and likelihood to posterior",
      "explanation": "Bayes updates beliefs with evidence."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 5: `studio_quiz-005`

- **Variation:** per_concept
- **Tags:** cbse, physics, scope_mode:per_concept, source_pdf:leph201
- **scope_mode:** per_concept

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

**Custom Instructions:**

4 MCQs, medium, lens formula and magnification

**Expected output**

**Quiz Json:**

{
  "title": "Lens Formula Focus",
  "questions": [
    {
      "question": "Lens formula is:",
      "options": [
        "1/f=1/v+1/u",
        "1/f=1/v-1/u",
        "f=uv",
        "f=u+v"
      ],
      "correct_answer": "1/f=1/v-1/u",
      "explanation": "Standard Cartesian lens formula."
    },
    {
      "question": "Magnification m equals:",
      "options": [
        "v/u",
        "u/v",
        "f/v",
        "v-f"
      ],
      "correct_answer": "v/u",
      "explanation": "m = v/u."
    },
    {
      "question": "Real object distance u is:",
      "options": [
        "Negative in Cartesian convention",
        "Always positive",
        "Zero",
        "Equal to f always"
      ],
      "correct_answer": "Negative in Cartesian convention",
      "explanation": "Sign convention for real object."
    },
    {
      "question": "Lens power P in dioptre when f in metres:",
      "options": [
        "P=f",
        "P=1/f",
        "P=f²",
        "P=2f"
      ],
      "correct_answer": "P=1/f",
      "explanation": "Power reciprocal of focal length."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

## Variation: `multi_concept`


#### Example 1: `studio_quiz-006`

- **Variation:** multi_concept
- **Tags:** cbse, physics, scope_mode:multi_concept, source_pdf:leph103
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

6 MCQs, medium, full chapter breadth — no narrow topic

**Expected output**

**Quiz Json:**

{
  "title": "Current Electricity Full Breadth",
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
    },
    {
      "question": "Parallel resistors 6 Ω and 3 Ω give R_eq:",
      "options": [
        "2 Ω",
        "9 Ω",
        "18 Ω",
        "1 Ω"
      ],
      "correct_answer": "2 Ω",
      "explanation": "1/R_eq=1/6+1/3=1/2 → R_eq=2 Ω."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-007`

- **Variation:** multi_concept
- **Tags:** cbse, biology, scope_mode:multi_concept, source_pdf:kebo110
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2. Mitosis: growth/repair, same chromosome number. Meiosis: gametes, halves chromosomes. Prophase I: crossing over.

**Custom Instructions:**

5 MCQs, medium, cover all topics in context

**Expected output**

**Quiz Json:**

{
  "title": "Photosynthesis & Cell Division Mix",
  "questions": [
    {
      "question": "Light reaction products include:",
      "options": [
        "ATP and NADPH",
        "Only CO2",
        "Only glucose",
        "Only O2 absorbed"
      ],
      "correct_answer": "ATP and NADPH",
      "explanation": "Light reaction outputs ATP, NADPH."
    },
    {
      "question": "Calvin cycle location:",
      "options": [
        "Grana",
        "Stroma",
        "Mitochondria",
        "Nucleus"
      ],
      "correct_answer": "Stroma",
      "explanation": "CO2 fixation in stroma."
    },
    {
      "question": "Mitosis purpose:",
      "options": [
        "Gamete formation",
        "Growth and repair with same chromosome number",
        "Halving chromosomes",
        "Crossing over"
      ],
      "correct_answer": "Growth and repair with same chromosome number",
      "explanation": "Mitosis maintains 2n."
    },
    {
      "question": "Meiosis produces:",
      "options": [
        "Identical somatic cells",
        "Gametes with halved chromosomes",
        "Only proteins",
        "Chlorophyll"
      ],
      "correct_answer": "Gametes with halved chromosomes",
      "explanation": "Meiosis → n for gametes."
    },
    {
      "question": "Crossing over occurs in:",
      "options": [
        "Prophase I of meiosis",
        "Mitotic prophase always",
        "Cytokinesis",
        "G1 only"
      ],
      "correct_answer": "Prophase I of meiosis",
      "explanation": "Prophase I exchanges segments."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 3: `studio_quiz-008`

- **Variation:** multi_concept
- **Tags:** cbse, chemistry, scope_mode:multi_concept, source_pdf:kech106
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Kc=[products]/[reactants] at equilibrium. Le Chatelier: stress shifts to oppose change. Catalyst speeds approach, not K. Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.

**Custom Instructions:**

5 MCQs, hard, all selected sources

**Expected output**

**Quiz Json:**

{
  "title": "Equilibrium & Electrochemistry Combined",
  "questions": [
    {
      "question": "Kc uses:",
      "options": [
        "Equilibrium molar concentrations",
        "Only solids",
        "Initial concentrations",
        "Temperature only"
      ],
      "correct_answer": "Equilibrium molar concentrations",
      "explanation": "Kc defined at equilibrium."
    },
    {
      "question": "Catalyst effect on K:",
      "options": [
        "No change to K",
        "Doubles K",
        "Halves K",
        "Eliminates K"
      ],
      "correct_answer": "No change to K",
      "explanation": "Catalyst affects rate not K."
    },
    {
      "question": "Galvanic cell anode undergoes:",
      "options": [
        "Reduction",
        "Oxidation",
        "No reaction",
        "Hydrolysis"
      ],
      "correct_answer": "Oxidation",
      "explanation": "Anode = oxidation site."
    },
    {
      "question": "E°cell equals:",
      "options": [
        "E°cathode-E°anode",
        "E°anode-E°cathode",
        "Zero always",
        "Sum of resistances"
      ],
      "correct_answer": "E°cathode-E°anode",
      "explanation": "Standard cell EMF formula."
    },
    {
      "question": "Le Chatelier: increase pressure on gas reaction with fewer product moles shifts:",
      "options": [
        "Toward fewer moles side",
        "Toward more moles side",
        "No shift",
        "Stops reaction"
      ],
      "correct_answer": "Toward fewer moles side",
      "explanation": "System opposes pressure increase."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 4: `studio_quiz-009`

- **Variation:** multi_concept
- **Tags:** cbse, mathematics, scope_mode:multi_concept, source_pdf:kemh107
- **scope_mode:** multi_concept

**Inputs**

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd. P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

**Custom Instructions:**

4 MCQs, medium, full breadth binomial and probability

**Expected output**

**Quiz Json:**

{
  "title": "Binomial & Probability Breadth",
  "questions": [
    {
      "question": "General term in (a+b)^n:",
      "options": [
        "Tr+1=nCr a^(n-r) b^r",
        "n!",
        "a+b",
        "n^r"
      ],
      "correct_answer": "Tr+1=nCr a^(n-r) b^r",
      "explanation": "Binomial theorem term."
    },
    {
      "question": "nCr counts:",
      "options": [
        "Combinations",
        "Permutations only",
        "Integrals",
        "Derivatives"
      ],
      "correct_answer": "Combinations",
      "explanation": "Binomial coefficients are combinations."
    },
    {
      "question": "P(A∪B) equals:",
      "options": [
        "P(A)+P(B)-P(A∩B)",
        "P(A)P(B)",
        "1",
        "P(A)-P(B)"
      ],
      "correct_answer": "P(A)+P(B)-P(A∩B)",
      "explanation": "Addition theorem."
    },
    {
      "question": "Independent events satisfy:",
      "options": [
        "P(A∩B)=P(A)P(B)",
        "P(A)=P(B)",
        "P(A)=0",
        "P(A)=1"
      ],
      "correct_answer": "P(A∩B)=P(A)P(B)",
      "explanation": "Definition of independence."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

## Variation: `per_source`


#### Example 1: `studio_quiz-010`

- **Variation:** per_source
- **Tags:** cbse, physics, scope_mode:per_source, source_pdf:leph103
- **scope_mode:** per_source

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

5 MCQs, easy, CBSE board style

**Expected output**

**Quiz Json:**

{
  "title": "CBSE Current Electricity Easy",
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

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-011`

- **Variation:** per_source
- **Tags:** cbse, biology, scope_mode:per_source, source_pdf:lebo105
- **scope_mode:** per_source

**Inputs**

**Context:**

DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.

**Custom Instructions:**

5 MCQs, medium, molecular inheritance

**Expected output**

**Quiz Json:**

{
  "title": "DNA & Inheritance Quiz",
  "questions": [
    {
      "question": "Adenine pairs with:",
      "options": [
        "Guanine",
        "Thymine",
        "Cytosine only",
        "Uracil always"
      ],
      "correct_answer": "Thymine",
      "explanation": "A-T pairing in DNA."
    },
    {
      "question": "DNA replication is:",
      "options": [
        "Conservative",
        "Semiconservative",
        "Dispersive only",
        "Random"
      ],
      "correct_answer": "Semiconservative",
      "explanation": "One old + one new strand."
    },
    {
      "question": "mRNA function:",
      "options": [
        "Carries genetic code to ribosomes",
        "Stores lipid",
        "Catalyses pepsin",
        "Absorbs light"
      ],
      "correct_answer": "Carries genetic code to ribosomes",
      "explanation": "mRNA template for translation."
    },
    {
      "question": "Guanine pairs with:",
      "options": [
        "Adenine",
        "Thymine",
        "Cytosine",
        "Glucose"
      ],
      "correct_answer": "Cytosine",
      "explanation": "G-C base pair."
    },
    {
      "question": "Translation occurs at:",
      "options": [
        "Ribosomes",
        "Grana only",
        "Stomata",
        "Casparian strip"
      ],
      "correct_answer": "Ribosomes",
      "explanation": "Protein synthesis on ribosomes."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 3: `studio_quiz-012`

- **Variation:** per_source
- **Tags:** cbse, chemistry, scope_mode:per_source, source_pdf:lech203
- **scope_mode:** per_source

**Inputs**

**Context:**

Tollens' test: silver mirror with aldehydes, not ketones. C=O undergoes nucleophilic addition.

**Custom Instructions:**

4 MCQs, medium, carbonyl tests

**Expected output**

**Quiz Json:**

{
  "title": "Aldehydes & Ketones Tests",
  "questions": [
    {
      "question": "Tollens' test positive for:",
      "options": [
        "Aldehydes",
        "Ketones only",
        "Alkanes",
        "Ethers"
      ],
      "correct_answer": "Aldehydes",
      "explanation": "Aldehydes reduce Ag+ to silver mirror."
    },
    {
      "question": "Ketones with Tollens' reagent:",
      "options": [
        "No silver mirror",
        "Always positive",
        "Explode",
        "Form gas only"
      ],
      "correct_answer": "No silver mirror",
      "explanation": "Ketones don't reduce Tollens' reagent."
    },
    {
      "question": "C=O group undergoes:",
      "options": [
        "Nucleophilic addition",
        "Only free radical substitution",
        "No reactions",
        "Only elimination always"
      ],
      "correct_answer": "Nucleophilic addition",
      "explanation": "Polarized carbonyl carbon attacked by nucleophile."
    },
    {
      "question": "Tollens' produces:",
      "options": [
        "Silver mirror on aldehyde oxidation",
        "Blue copper solution",
        "White precipitate always",
        "No visible change always"
      ],
      "correct_answer": "Silver mirror on aldehyde oxidation",
      "explanation": "Characteristic silver mirror test."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 4: `studio_quiz-013`

- **Variation:** per_source
- **Tags:** cbse, mathematics, scope_mode:per_source, source_pdf:lemh205
- **scope_mode:** per_source

**Inputs**

**Context:**

Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.

**Custom Instructions:**

5 MCQs, hard, 3D geometry

**Expected output**

**Quiz Json:**

{
  "title": "Three Dimensional Geometry",
  "questions": [
    {
      "question": "Direction cosines satisfy:",
      "options": [
        "l²+m²+n²=1",
        "l+m+n=0",
        "l=m=n=0",
        "l²+m²=n"
      ],
      "correct_answer": "l²+m²+n²=1",
      "explanation": "Unit direction vector constraint."
    },
    {
      "question": "Line through (x1,y1,z1) with direction a,b,c:",
      "options": [
        "(x-x1)/a=(y-y1)/b=(z-z1)/c",
        "x+y+z=0",
        "y=mx+c",
        "x²+y²=1"
      ],
      "correct_answer": "(x-x1)/a=(y-y1)/b=(z-z1)/c",
      "explanation": "Symmetric form of 3D line."
    },
    {
      "question": "Skew lines distance uses:",
      "options": [
        "Cross product of direction vectors",
        "Only dot product",
        "Determinant zero",
        "Single point only"
      ],
      "correct_answer": "Cross product of direction vectors",
      "explanation": "Shortest distance formula uses cross product."
    },
    {
      "question": "Direction cosines are cosines of angles with:",
      "options": [
        "Coordinate axes",
        "Only x-axis",
        "Random lines",
        "Normal only"
      ],
      "correct_answer": "Coordinate axes",
      "explanation": "Angles with x, y, z axes."
    },
    {
      "question": "A line in 3D requires:",
      "options": [
        "Point and direction ratios",
        "Only one point",
        "Only slope",
        "Area"
      ],
      "correct_answer": "Point and direction ratios",
      "explanation": "Point-direction form."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 5: `studio_quiz-014`

- **Variation:** per_source
- **Tags:** cbse, physics, scope_mode:per_source, source_pdf:keph106
- **scope_mode:** per_source

**Inputs**

**Context:**

Torque τ=rF sin θ. τ=Iα. Parallel axis: I=I_cm+Md².

**Custom Instructions:**

3 MCQs, easy, rotational dynamics thin source

**Expected output**

**Quiz Json:**

{
  "title": "Rotational Dynamics Quick",
  "questions": [
    {
      "question": "Torque magnitude equals:",
      "options": [
        "rF sin θ",
        "r/F",
        "F only",
        "r+F"
      ],
      "correct_answer": "rF sin θ",
      "explanation": "τ = rF sin θ."
    },
    {
      "question": "Rotational analog τ=Iα corresponds to:",
      "options": [
        "F=ma",
        "P=IV",
        "V=IR",
        "E=mc²"
      ],
      "correct_answer": "F=ma",
      "explanation": "I is rotational inertia."
    },
    {
      "question": "Parallel axis theorem:",
      "options": [
        "I=I_cm+Md²",
        "I=M/d",
        "I=0",
        "I=I_cm-Md²"
      ],
      "correct_answer": "I=I_cm+Md²",
      "explanation": "Shift parallel axis from CM."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

## Variation: `multi_source`


#### Example 1: `studio_quiz-015`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source, source_pdf:leph103
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Current Electricity] Ohm's law V=IR; resistivity ρ=RA/l.

[Source B — Electrochemistry] Galvanic cell: anode oxidation; E°cell=E°cathode-E°anode.

**Custom Instructions:**

5 MCQs, medium, integrate both sources

**Expected output**

**Quiz Json:**

{
  "title": "Electricity & Electrochemistry Integrated",
  "questions": [
    {
      "question": "Ohm's law states:",
      "options": [
        "V=IR",
        "V=I/R always",
        "I=0 always",
        "R=0 required"
      ],
      "correct_answer": "V=IR",
      "explanation": "Per electricity excerpt."
    },
    {
      "question": "Resistivity ρ relates to:",
      "options": [
        "R, A, l by ρ=RA/l",
        "Only voltage",
        "Only current direction",
        "Cell EMF"
      ],
      "correct_answer": "R, A, l by ρ=RA/l",
      "explanation": "Material geometry relation."
    },
    {
      "question": "Galvanic cell anode:",
      "options": [
        "Oxidation",
        "Reduction",
        "Salt bridge only",
        "Insulator"
      ],
      "correct_answer": "Oxidation",
      "explanation": "Per electrochemistry excerpt."
    },
    {
      "question": "Standard E°cell:",
      "options": [
        "E°cathode-E°anode",
        "E°anode only",
        "Sum of ρ",
        "1/R_eq"
      ],
      "correct_answer": "E°cathode-E°anode",
      "explanation": "Cell EMF definition."
    },
    {
      "question": "Both topics link through:",
      "options": [
        "Charge flow and energy conversion",
        "Only optics",
        "Only digestion",
        "Random guess"
      ],
      "correct_answer": "Charge flow and energy conversion",
      "explanation": "Integrated concept bridge."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-016`

- **Variation:** multi_source
- **Tags:** cbse, biology, scope_mode:multi_source
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Photosynthesis] Light reaction in grana; Calvin cycle in stroma.

[Source B — Cell division] Mitosis maintains chromosome number; meiosis halves for gametes.

**Custom Instructions:**

5 MCQs, medium, both biology sources

**Expected output**

**Quiz Json:**

{
  "title": "Photosynthesis & Meiosis Synthesis",
  "questions": [
    {
      "question": "Calvin cycle fixes:",
      "options": [
        "CO2 in stroma",
        "O2 in grana only",
        "N2 in nucleus",
        "Glucose in mouth"
      ],
      "correct_answer": "CO2 in stroma",
      "explanation": "Photosynthesis excerpt."
    },
    {
      "question": "Light reaction location:",
      "options": [
        "Grana",
        "Stroma only",
        "Villi",
        "Casparian strip"
      ],
      "correct_answer": "Grana",
      "explanation": "Thylakoid membranes in grana."
    },
    {
      "question": "Meiosis reduces:",
      "options": [
        "Chromosome number for gametes",
        "ATP only",
        "CO2",
        "Resistivity"
      ],
      "correct_answer": "Chromosome number for gametes",
      "explanation": "Cell division excerpt."
    },
    {
      "question": "Mitosis used for:",
      "options": [
        "Growth and repair",
        "Gamete formation only",
        "Silver mirror test",
        "Lens formula"
      ],
      "correct_answer": "Growth and repair",
      "explanation": "Maintains 2n."
    },
    {
      "question": "Both processes involve:",
      "options": [
        "Energy/transformations in living cells",
        "Only metal ions",
        "Only optics",
        "None"
      ],
      "correct_answer": "Energy/transformations in living cells",
      "explanation": "Integrated biology theme."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 3: `studio_quiz-017`

- **Variation:** multi_source
- **Tags:** cbse, mathematics, scope_mode:multi_source
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Probability] P(E)=favourable/total; P(A∩B)=P(A)P(B) if independent.

[Source B — Binomial] Tr+1=nCr a^(n-r) b^r in (a+b)^n expansion.

**Custom Instructions:**

4 MCQs, hard, probability and binomial

**Expected output**

**Quiz Json:**

{
  "title": "Probability-Binomial Integration",
  "questions": [
    {
      "question": "Tr+1 in binomial expansion:",
      "options": [
        "nCr a^(n-r) b^r",
        "P(A)+P(B)",
        "l²+m²+n²=1",
        "V=IR"
      ],
      "correct_answer": "nCr a^(n-r) b^r",
      "explanation": "Binomial term."
    },
    {
      "question": "Classical probability:",
      "options": [
        "favourable/total",
        "nCr only",
        "f only",
        "Zero"
      ],
      "correct_answer": "favourable/total",
      "explanation": "Probability definition."
    },
    {
      "question": "Independent events:",
      "options": [
        "P(A∩B)=P(A)P(B)",
        "P(A)=1 always",
        "P(A)=0 always",
        "No formula"
      ],
      "correct_answer": "P(A∩B)=P(A)P(B)",
      "explanation": "Independence rule."
    },
    {
      "question": "Binomial coefficients count:",
      "options": [
        "Combinations in expansion",
        "Only permutations",
        "Only angles",
        "Resistances"
      ],
      "correct_answer": "Combinations in expansion",
      "explanation": "nCr in expansion."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 4: `studio_quiz-018`

- **Variation:** multi_source
- **Tags:** cbse, chemistry, scope_mode:multi_source
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Current Electricity] Ohm's law V=IR; resistivity ρ=RA/l.

[Source B — Electrochemistry] Galvanic cell: anode oxidation; E°cell=E°cathode-E°anode.

**Custom Instructions:**

5 MCQs, medium, cross-domain chemistry-physics

**Expected output**

**Quiz Json:**

{
  "title": "Material Properties Cross-Source",
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
      "question": "E°cell definition uses:",
      "options": [
        "Standard electrode potentials",
        "Only ρ",
        "Only m",
        "Lens formula"
      ],
      "correct_answer": "Standard electrode potentials",
      "explanation": "Electrochemistry source."
    },
    {
      "question": "Anode in galvanic cell:",
      "options": [
        "Oxidation site",
        "Reduction only",
        "Salt only",
        "Mirror test"
      ],
      "correct_answer": "Oxidation site",
      "explanation": "Electrode role."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 5: `studio_quiz-019`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source, source_pdf:leph201
- **scope_mode:** multi_source

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

6 MCQs, medium, optics and electricity selected

**Expected output**

**Quiz Json:**

{
  "title": "Optics & Electricity Multi-Source",
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
      "question": "Lens power P:",
      "options": [
        "1/f with f in metres",
        "V=IR",
        "I=neAv_d",
        "ρ=0"
      ],
      "correct_answer": "1/f with f in metres",
      "explanation": "Optics source."
    },
    {
      "question": "Real object u sign:",
      "options": [
        "Negative",
        "Always positive",
        "Zero",
        "Complex"
      ],
      "correct_answer": "Negative",
      "explanation": "Sign convention."
    },
    {
      "question": "Magnification:",
      "options": [
        "v/u",
        "R_eq",
        "P(A∩B)",
        "nCr"
      ],
      "correct_answer": "v/u",
      "explanation": "Lens magnification."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 6: `studio_quiz-020`

- **Variation:** multi_source
- **Tags:** neet, biology, scope_mode:multi_source
- **scope_mode:** multi_source

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.

**Custom Instructions:**

5 MCQs, hard NEET, both sources

**Expected output**

**Quiz Json:**

{
  "title": "NEET Digestion-Photosynthesis Deck",
  "questions": [
    {
      "question": "Salivary amylase acts in:",
      "options": [
        "Mouth",
        "Stomach",
        "Grana",
        "Stroma"
      ],
      "correct_answer": "Mouth",
      "explanation": "Digestion source."
    },
    {
      "question": "Calvin cycle:",
      "options": [
        "CO2 fixation in stroma",
        "Light in grana only",
        "Pepsin activation",
        "Tollens test"
      ],
      "correct_answer": "CO2 fixation in stroma",
      "explanation": "Photosynthesis source."
    },
    {
      "question": "Pepsin needs:",
      "options": [
        "Acidic stomach",
        "Alkaline duodenum only",
        "No pH",
        "Only light"
      ],
      "correct_answer": "Acidic stomach",
      "explanation": "Enzyme environment."
    },
    {
      "question": "ATP from light reaction used for:",
      "options": [
        "Calvin cycle",
        "Only digestion",
        "Only optics",
        "None"
      ],
      "correct_answer": "Calvin cycle",
      "explanation": "Cross-process link."
    },
    {
      "question": "Absorption mainly in:",
      "options": [
        "Small intestine",
        "Grana",
        "Lens",
        "Anode"
      ],
      "correct_answer": "Small intestine",
      "explanation": "Digestion source."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

## Variation: `no_source`


#### Example 1: `studio_quiz-021`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source

**Inputs**

**Context:**



**Custom Instructions:**

5 MCQs, easy, general science — no source provided

**Expected output**

**Quiz Json:**

{
  "title": "General Science Baseline",
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
      "explanation": "Coherent general science item."
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
      "explanation": "Basic chemistry literacy."
    },
    {
      "question": "Plants need for photosynthesis:",
      "options": [
        "Light",
        "Only darkness",
        "Only metal",
        "Vacuum"
      ],
      "correct_answer": "Light",
      "explanation": "General biology."
    },
    {
      "question": "Sum of angles in triangle:",
      "options": [
        "180°",
        "90°",
        "360°",
        "0°"
      ],
      "correct_answer": "180°",
      "explanation": "Euclidean geometry."
    },
    {
      "question": "Speed unit in SI:",
      "options": [
        "m/s",
        "km only",
        "mph",
        "Light-year"
      ],
      "correct_answer": "m/s",
      "explanation": "Units knowledge."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-022`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source

**Inputs**

**Context:**



**Custom Instructions:**

3 MCQs, medium, coherent topic without indexed source

**Expected output**

**Quiz Json:**

{
  "title": "Study Skills Mini Quiz",
  "questions": [
    {
      "question": "Active recall means:",
      "options": [
        "Testing yourself on material",
        "Only re-reading",
        "Skipping revision",
        "Ignoring errors"
      ],
      "correct_answer": "Testing yourself on material",
      "explanation": "Metacognition item."
    },
    {
      "question": "Spaced repetition helps:",
      "options": [
        "Long-term retention",
        "Only cramming",
        "Avoiding sleep",
        "Deleting notes"
      ],
      "correct_answer": "Long-term retention",
      "explanation": "Learning strategy."
    },
    {
      "question": "Before exams, prioritise:",
      "options": [
        "Weak topics with timed practice",
        "Only easy topics",
        "Zero practice",
        "Random guessing"
      ],
      "correct_answer": "Weak topics with timed practice",
      "explanation": "Exam strategy."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

## Variation: `custom_override`


#### Example 1: `studio_quiz-023`

- **Variation:** custom_override
- **Tags:** cbse, physics, custom_instructions, scope_mode:per_concepthard
- **scope_mode:** per_concepthard

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

7 MCQs, hard difficulty, numerical reasoning emphasis

**Expected output**

**Quiz Json:**

{
  "title": "Hard Numerical Electricity",
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
    },
    {
      "question": "Parallel resistors 6 Ω and 3 Ω give R_eq:",
      "options": [
        "2 Ω",
        "9 Ω",
        "18 Ω",
        "1 Ω"
      ],
      "correct_answer": "2 Ω",
      "explanation": "1/R_eq=1/6+1/3=1/2 → R_eq=2 Ω."
    },
    {
      "question": "Ohm's law applies best to:",
      "options": [
        "Ohmic conductors at constant T",
        "All materials at any T",
        "Only superconductors",
        "Only insulators"
      ],
      "correct_answer": "Ohmic conductors at constant T",
      "explanation": "V=IR holds for ohmic conductors at fixed temperature."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 2: `studio_quiz-024`

- **Variation:** custom_override
- **Tags:** cbse, biology, custom_instructions, scope_mode:per_concepteasy
- **scope_mode:** per_concepteasy

**Inputs**

**Context:**

Dicot root: radial vascular bundle. Monocot: polyarch xylem. Casparian strip in endodermis controls flow.

**Custom Instructions:**

3 MCQs, easy, Casparian strip only

**Expected output**

**Quiz Json:**

{
  "title": "Casparian Strip Easy",
  "questions": [
    {
      "question": "Casparian strip located in:",
      "options": [
        "Endodermis",
        "Epidermis only",
        "Stomata",
        "Grana"
      ],
      "correct_answer": "Endodermis",
      "explanation": "Endodermal barrier."
    },
    {
      "question": "Casparian strip made of:",
      "options": [
        "Suberin",
        "Only chlorophyll",
        "Silver",
        "Only lipase"
      ],
      "correct_answer": "Suberin",
      "explanation": "Waxy suberin band."
    },
    {
      "question": "Its function:",
      "options": [
        "Controls apoplastic flow into stele",
        "Produces ATP",
        "Fixes CO2",
        "Forms images"
      ],
      "correct_answer": "Controls apoplastic flow into stele",
      "explanation": "Forces selective uptake."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---

#### Example 3: `studio_quiz-025`

- **Variation:** custom_override
- **Tags:** cbse, mathematics, custom_instructions, scope_mode:per_conceptlanguage
- **scope_mode:** per_conceptlanguage

**Inputs**

**Context:**

Parabola: focus-directrix equidistance. y²=4ax focus (a,0). e=1 for parabola.

**Custom Instructions:**

5 MCQs, medium, focus parabola only — Hindi technical terms allowed in explanations

**Expected output**

**Quiz Json:**

{
  "title": "Parabola Focus Drill",
  "questions": [
    {
      "question": "Parabola locus definition:",
      "options": [
        "Equidistant from focus and directrix",
        "Circle centre",
        "Hyperbola asymptote",
        "Ellipse sum"
      ],
      "correct_answer": "Equidistant from focus and directrix",
      "explanation": "Geometric definition."
    },
    {
      "question": "y²=4ax focus at:",
      "options": [
        "(a,0)",
        "(0,a)",
        "(-a,0)",
        "(0,-a)"
      ],
      "correct_answer": "(a,0)",
      "explanation": "Standard parabola focus."
    },
    {
      "question": "Parabola eccentricity:",
      "options": [
        "1",
        "0",
        "2",
        "<1"
      ],
      "correct_answer": "1",
      "explanation": "e=1 always for parabola."
    },
    {
      "question": "Directrix of y²=4ax:",
      "options": [
        "x=-a",
        "x=a",
        "y=0",
        "y=a"
      ],
      "correct_answer": "x=-a",
      "explanation": "Directrix line."
    },
    {
      "question": "Axis of parabola y²=4ax:",
      "options": [
        "x-axis",
        "y-axis only",
        "z-axis",
        "None"
      ],
      "correct_answer": "x-axis",
      "explanation": "Opens along x-axis."
    }
  ]
}

**Quality Check:** question_count: pass. schema_valid: pass. options_quality: pass. grounding: pass.

---
