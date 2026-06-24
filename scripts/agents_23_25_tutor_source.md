## 23. Tutor Notebook Bootstrap Agent

| Field | Value |
|-------|-------|
| Dataset ID | `tutor_notebook_bootstrap` |
| Category | Tutor Mode |
| Tier | Tier 2 |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.4.0 |

**Agent responsibility:** Generate the first-open tutor notebook payload: opening summary (Markdown), four suggestion chips, and ranked studio recommendations with exactly two auto_generate tools. Production: [`tutor/notebook_bootstrap.j2`](packages/core/prompts/templates/tutor/notebook_bootstrap.j2).

**Audit finding (baseline v1.0.0):** Baseline v1.0.0 used duplicate suggestion chips, two-line opening summaries, mismatched NCERT context (e.g. photosynthesis text for digestion chapter), and generic quiz+flashcards for every subject. Rebuilt with catalog-locked class/chapter/concept scopes, aligned NCERT snippets, and production LLM gold via TutorNotebookBootstrapService sanitization rules.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Formula-heavy science chapters | 2 |
| `conversational` | Natural student onboarding | 2 |
| `diagram` | Visual / ray-diagram chapters | 2 |
| `cbse` | Board exam framing | 1 |
| `neet` | NEET-oriented biology/chemistry | 1 |
| `jee` | JEE-style physics depth | 1 |
| `multi_part` | Multi-concept chapters | 1 |
| `conceptual` | Theory-first chapters | 1 |
| `case_study` | Social science narrative | 1 |
| `ncert_strict` | Strict NCERT vocabulary | 1 |
| `typo` | Robust to minor typos in scope | 1 |
| `proof` | Derivation-heavy maths | 1 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **opening_structure** — opening_summary has Summary, Key topics, Exam highlights, Ask me for full clarity.
* **suggestions_unique** — Exactly 4 unique label/prompt pairs, labels ≤28 chars.
* **studio_pair** — All 4 studio types present; exactly 2 auto_generate=true, subject-aware ranking.
* **ncert_grounding** — Facts in summary trace to ncert_context; no invented syllabus.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `class_num`, `subject_label`, `chapter_no`, `chapter_title`, `ncert_context`, `concept`
* Output keys: `bootstrap_json`

**Prompt template (production):**

```jinja2
You are ScholarSync Tutor, an NCERT-aligned study coach for Indian school students.



## Student scope

- Class: {{ class_num }}

- Subject: {{ subject_label }}

- Chapter: {{ chapter_no }} — {{ chapter_title }}

{% if concept %}

- Focus concept: {{ concept }}

{% else %}

- Focus: All concepts in this chapter

{% endif %}



## NCERT context (only source of facts)

{{ ncert_context }}



## Task

Return JSON only (no markdown fences) matching this schema:

{

  "opening_summary": string,

  "suggestions": [{"label": string, "prompt": string}],

  "studio_recommendations": [{"type": "flashcards"|"quiz"|"mind_map"|"slide_deck", "reason": string, "auto_generate": boolean}]

}



### opening_summary rules

Write Markdown for the first message the student sees. Use this exact structure:



## Summary



### Key topics

- bullet with **bold key term** for each main idea (3–5 bullets)

- ...



### Exam highlights

- bullet for exam-relevant facts, dates, formulas, or distinctions (2–4 bullets)

- ...



### Ask me for full clarity

1. numbered clarifying question you would ask the student

2. ...

3. ...



Tap a suggestion below or ask your own question.



Keep total length roughly 180–280 words. Ground every factual claim in NCERT context. If context is thin, say what is known and what to explore next — do not invent facts.



### suggestions rules

Return exactly 4 chips. Each must be specific to this chapter/concept (never generic "Main topics").

- Labels: ≤28 chars, student-friendly

- Prompts: full question ready to send; mention chapter/concept by name



### studio_recommendations rules

Rank **all 4** tools by value for THIS chapter (include every type once): flashcards, quiz, mind_map, slide_deck.

- Set `auto_generate: true` on **exactly the top 2** in your ranked order; all others `auto_generate: false`

- **Do not** default to flashcards + quiz unless the NCERT content is definition/formula heavy

- Pick the pair that best matches chapter content and subject:

  - Civics / history / geography / narrative social science → **slide_deck + quiz** (common)

  - Economics / interconnected policy topics → **mind_map + quiz**

  - Science definitions, formulas, terminology → **flashcards + quiz**

  - Math problem-solving → **quiz + flashcards** or **quiz + mind_map** when many subtopics

  - Single concept focus → **flashcards + quiz** only if recall practice is the main need

Include a one-line `reason` per tool (stored for debugging).
```

*Runtime note:* `TutorNotebookBootstrapService._generate_bootstrap_payload()` on notebook first open.

### Evaluation examples (15)
## Variation: `numerical`


#### Example 1: `tutor_notebook_bootstrap-001`

- **Variation:** numerical
- **Tags:** cbse, science, tutor_mode, numerical, production_llm_gold

**Inputs**

**Class Num:**

10

**Subject Label:**

Science

**Chapter No:**

12

**Chapter Title:**

Electricity

**Ncert Context:**

NCERT Class 10 Science Ch.12: Ohm's law V=IR at constant temperature. Resistance R=ρL/A. Resistors in series add; in parallel reciprocals add. Electric power P=VI=I²R. Household circuits use 220 V AC. Focus: Electricity exam prep.

**Concept:**

Ohm's law and resistance

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Ohm's Law**: The relationship between voltage (V), current (I), and resistance (R) is defined by the equation V = IR at constant temperature.\n- **Resistance**: Resistance (R) is calculated using the formula R = ρL/A, where ρ is resistivity, L is length, and A is cross-sectional area.\n- **Series and Parallel Resistors**: Resistors in series add directly, while resistors in parallel add using the reciprocal formula.\n- **Electric Power**: Power (P) can be calculated using P = VI or P = I²R, which shows how power relates to voltage and current.\n\n### Exam highlights\n- Remember the formula for Ohm's Law: V = IR.\n- Understand how to calculate total resistance in series and parallel circuits.\n- Electric power is crucial for understanding household circuits, which typically operate at 220 V AC.\n\n### Ask me for full clarity\n1. What is the significance of resistivity in the resistance formula?\n2. Can you explain how to calculate total resistance in a series circuit?\n3. What are the practical applications of Ohm's Law in everyday life?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain Ohm's Law",
      "prompt": "Can you explain Ohm's Law and its significance in Chapter 12?"
    },
    {
      "label": "Resistance Calculation",
      "prompt": "How do you calculate resistance using the formula R = ρL/A?"
    },
    {
      "label": "Series vs Parallel",
      "prompt": "What is the difference between resistors in series and parallel?"
    },
    {
      "label": "Electric Power Formulas",
      "prompt": "What are the different formulas for calculating electric power?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards will help memorize key definitions and formulas.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz can test understanding of Ohm's Law and resistance concepts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can visually organize the relationships between concepts.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "A slide deck can summarize key points for revision.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_notebook_bootstrap-015`

- **Variation:** numerical
- **Tags:** cbse, chemistry, tutor_mode, numerical, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

3

**Chapter Title:**

Electrochemistry

**Ncert Context:**

NCERT Class 12 Chemistry Ch.3: Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration. Focus: Electrochemistry exam prep.

**Concept:**

Nernst equation

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Galvanic cell**: A device that converts chemical energy into electrical energy through redox reactions.\n- **Anode and cathode**: The anode is where oxidation occurs, while the cathode is where reduction takes place.\n- **Standard cell potential (E°cell)**: Calculated as E°cell = E°cathode - E°anode, indicating the driving force of the reaction.\n- **Nernst equation**: Relates the electromotive force (EMF) of a cell to the concentration of reactants and products.\n\n### Exam highlights\n- The Nernst equation is essential for calculating cell potential under non-standard conditions.\n- Remember the formula: E = E° - (RT/nF) * ln(Q), where Q is the reaction quotient.\n- Key to understand how concentration affects cell potential.\n\n### Ask me for full clarity\n1. What specific aspect of the Nernst equation do you find challenging?\n2. Can you explain the significance of standard conditions in electrochemistry?\n3. How does the concentration of ions affect the EMF of a galvanic cell?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Nernst equation details",
      "prompt": "Can you explain the components of the Nernst equation in Chapter 3?"
    },
    {
      "label": "Understanding E°cell",
      "prompt": "What does E°cell represent in electrochemistry, and how is it calculated?"
    },
    {
      "label": "Oxidation vs Reduction",
      "prompt": "Can you clarify the difference between oxidation and reduction in a galvanic cell?"
    },
    {
      "label": "Application of Nernst",
      "prompt": "How can the Nernst equation be applied to real-life electrochemical cells?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Useful for memorizing key terms and equations related to the Nernst equation.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Helps assess understanding of the Nernst equation and related concepts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Visual representation of concepts and their interconnections in electrochemistry.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Effective for summarizing and presenting key ideas from the chapter.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `conversational`


#### Example 1: `tutor_notebook_bootstrap-002`

- **Variation:** conversational
- **Tags:** cbse, biology, tutor_mode, conversational, production_llm_gold

**Inputs**

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

16

**Chapter Title:**

Digestion and Absorption

**Ncert Context:**

NCERT Class 11 Biology Ch.16: Salivary amylase in mouth. Stomach: HCl and pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi and microvilli. Focus: Digestion and Absorption exam prep.

**Concept:**



**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Salivary amylase** initiates starch digestion in the mouth.\n- **HCl and pepsin** in the stomach aid protein digestion.\n- **Pancreatic juice** contains enzymes like trypsin, lipase, and amylase for further digestion in the small intestine.\n- **Villi and microvilli** in the small intestine enhance nutrient absorption.\n\n### Exam highlights\n- Remember that salivary amylase breaks down carbohydrates into simpler sugars.\n- HCl creates an acidic environment for pepsin to function optimally.\n- Pancreatic enzymes are crucial for digesting proteins, fats, and carbohydrates.\n- Absorption mainly occurs through the extensive surface area provided by villi and microvilli.\n\n### Ask me for full clarity\n1. What role does each enzyme play in digestion?\n2. How does the structure of the small intestine facilitate absorption?\n3. Can you explain the significance of HCl in the stomach?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Role of enzymes",
      "prompt": "What role does each enzyme play in digestion in Chapter 16?"
    },
    {
      "label": "Small intestine structure",
      "prompt": "How does the structure of the small intestine facilitate absorption in Chapter 16?"
    },
    {
      "label": "Significance of HCl",
      "prompt": "Can you explain the significance of HCl in the stomach as discussed in Chapter 16?"
    },
    {
      "label": "Functions of villi",
      "prompt": "What are the functions of villi and microvilli in nutrient absorption in Chapter 16?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards will help memorize key terms and definitions related to digestion.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz can test understanding of the digestion process and enzyme functions.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can visually organize the digestion process and enzyme interactions.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "A slide deck can summarize key concepts and facilitate review for exams.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_notebook_bootstrap-013`

- **Variation:** conversational
- **Tags:** cbse, geography, tutor_mode, conversational, production_llm_gold

**Inputs**

**Class Num:**

10

**Subject Label:**

Geography

**Chapter No:**

1

**Chapter Title:**

Resources and Development

**Ncert Context:**

NCERT Class 10 Geography Ch.1: Resource types: renewable, non-renewable. Sustainable development balances present and future needs. Soil erosion and conservation. Focus: Resources and Development exam prep.

**Concept:**



**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Resource types**: Understand the difference between renewable and non-renewable resources.\n- **Sustainable development**: Learn how to balance present and future needs for resources.\n- **Soil erosion**: Explore the causes and effects of soil erosion on agriculture and environment.\n- **Soil conservation**: Discover various methods to conserve soil and maintain its fertility.\n\n### Exam highlights\n- Renewable resources can be replenished naturally, while non-renewable resources are finite.\n- Sustainable development aims to meet the needs of the present without compromising future generations.\n- Soil erosion can be caused by water, wind, and human activities, leading to loss of fertile land.\n\n### Ask me for full clarity\n1. What are the main differences between renewable and non-renewable resources?\n2. Can you explain how sustainable development impacts resource management?\n3. What are some effective soil conservation techniques?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Types of resources",
      "prompt": "What are the key differences between renewable and non-renewable resources in Chapter 1?"
    },
    {
      "label": "Sustainable development",
      "prompt": "How does sustainable development balance present and future resource needs?"
    },
    {
      "label": "Soil erosion causes",
      "prompt": "What are the main causes of soil erosion discussed in Chapter 1?"
    },
    {
      "label": "Conservation methods",
      "prompt": "What methods of soil conservation are mentioned in the chapter?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "slide_deck",
      "reason": "Visual representation of key concepts will aid understanding.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Testing knowledge on definitions and concepts reinforces learning.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Organizing information visually helps in connecting ideas effectively.",
      "auto_generate": false
    },
    {
      "type": "flashcards",
      "reason": "Useful for memorizing key terms and definitions, but less critical than other tools.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `tutor_notebook_bootstrap-003`

- **Variation:** diagram
- **Tags:** cbse, physics, tutor_mode, diagram, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

9

**Chapter Title:**

Ray Optics and Optical Instruments

**Ncert Context:**

NCERT Class 12 Physics Ch.9: Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign convention: object distance u negative for real objects. Focus: Ray Optics and Optical Instruments exam prep.

**Concept:**

Lens formula

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Lens formula**: The relationship between object distance (u), image distance (v), and focal length (f) is expressed as 1/f = 1/v - 1/u.\n- **Magnification (m)**: Defined as the ratio of image distance to object distance, m = v/u.\n- **Power of a lens (P)**: The power is given by P = 1/f, where f is in meters.\n- **Sign convention**: For real objects, the object distance (u) is considered negative.\n\n### Exam highlights\n- Remember the lens formula and its components for solving problems related to lenses.\n- Understand the significance of magnification and how it affects image size.\n- Be familiar with the power of a lens and its unit (diopters).\n\n### Ask me for full clarity\n1. Can you explain how to apply the lens formula in different scenarios?\n2. What are the implications of the sign convention in lens calculations?\n3. How does magnification relate to the type of lens used?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain lens formula",
      "prompt": "Can you explain how to apply the lens formula in different scenarios from Chapter 9?"
    },
    {
      "label": "Sign convention details",
      "prompt": "What are the implications of the sign convention in lens calculations from Chapter 9?"
    },
    {
      "label": "Understanding magnification",
      "prompt": "How does magnification relate to the type of lens used in Chapter 9?"
    },
    {
      "label": "Power of a lens",
      "prompt": "What is the significance of the power of a lens in Chapter 9?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards will help reinforce definitions and formulas related to lenses.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz will test understanding of the lens formula and related concepts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can visually organize the relationships between concepts in lens optics.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "A slide deck can summarize key points and formulas for quick revision.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_notebook_bootstrap-014`

- **Variation:** diagram
- **Tags:** cbse, biology, tutor_mode, diagram, production_llm_gold

**Inputs**

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

13

**Chapter Title:**

Photosynthesis in Higher Plants

**Ncert Context:**

NCERT Class 11 Biology Ch.13: Light reaction in grana produces ATP, NADPH. Calvin cycle in stroma fixes CO₂. C3, C4 pathways differ in carbon fixation. Focus: Photosynthesis in Higher Plants exam prep.

**Concept:**

Calvin cycle

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Calvin cycle**: The process occurring in the stroma of chloroplasts that fixes CO₂ into organic molecules.\n- **C3 pathway**: The most common pathway of carbon fixation that occurs in plants like wheat and rice.\n- **C4 pathway**: A modified pathway that allows plants like maize and sugarcane to efficiently fix CO₂ in hot climates.\n- **ATP and NADPH**: Energy carriers produced during the light reactions that are essential for the Calvin cycle.\n\n### Exam highlights\n- The Calvin cycle is crucial for converting inorganic carbon into organic forms, a key concept in photosynthesis.\n- Distinction between C3 and C4 pathways is important; C4 plants have adaptations to minimize photorespiration.\n\n### Ask me for full clarity\n1. What specific aspect of the Calvin cycle do you find confusing?\n2. Do you want to know how the Calvin cycle relates to light reactions?\n3. Would you like examples of plants using C3 and C4 pathways?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain Calvin cycle",
      "prompt": "Can you explain the steps of the Calvin cycle in detail?"
    },
    {
      "label": "C3 vs C4 pathways",
      "prompt": "What are the differences between C3 and C4 pathways in photosynthesis?"
    },
    {
      "label": "Role of ATP and NADPH",
      "prompt": "How do ATP and NADPH contribute to the Calvin cycle?"
    },
    {
      "label": "Importance of photosynthesis",
      "prompt": "Why is photosynthesis, particularly the Calvin cycle, important for plants?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards will help in memorizing key terms and processes of the Calvin cycle.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz will test understanding of the Calvin cycle and its components.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can visually organize the relationships between C3 and C4 pathways.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "A slide deck can present the Calvin cycle and its significance in a structured format.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `tutor_notebook_bootstrap-004`

- **Variation:** cbse
- **Tags:** cbse, mathematics, tutor_mode, cbse, production_llm_gold

**Inputs**

**Class Num:**

10

**Subject Label:**

Mathematics

**Chapter No:**

4

**Chapter Title:**

Quadratic Equations

**Ncert Context:**

NCERT Class 10 Maths Ch.4: ax²+bx+c=0 roots via quadratic formula. Discriminant D=b²-4ac determines nature of roots. Sum of roots=-b/a; product=c/a. Focus: Quadratic Equations exam prep.

**Concept:**



**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Quadratic Equation**: Standard form is ax² + bx + c = 0.\n- **Roots**: Found using the quadratic formula, x = (-b ± √D) / 2a.\n- **Discriminant**: D = b² - 4ac determines the nature of roots.\n- **Sum and Product of Roots**: Sum = -b/a; Product = c/a.\n\n### Exam highlights\n- Remember the formula for roots and the significance of the discriminant.\n- Know how to derive the sum and product of roots from the coefficients.\n\n### Ask me for full clarity\n1. What is the significance of the discriminant in determining the nature of roots?\n2. Can you explain how to derive the quadratic formula?\n3. How do you find the sum and product of the roots from a given quadratic equation?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Discriminant details",
      "prompt": "What does the discriminant tell us about the roots in Quadratic Equations?"
    },
    {
      "label": "Finding roots",
      "prompt": "How do you use the quadratic formula to find the roots of a quadratic equation?"
    },
    {
      "label": "Sum and product",
      "prompt": "Can you explain how to calculate the sum and product of the roots from the coefficients?"
    },
    {
      "label": "Real-life applications",
      "prompt": "What are some real-life applications of quadratic equations?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "quiz",
      "reason": "Helps in practicing problem-solving skills for quadratic equations.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Visualizes the relationships between concepts in quadratic equations.",
      "auto_generate": true
    },
    {
      "type": "flashcards",
      "reason": "Reinforces key definitions and formulas related to quadratic equations.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Summarizes important concepts and formulas for revision.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `tutor_notebook_bootstrap-005`

- **Variation:** neet
- **Tags:** cbse, chemistry, tutor_mode, neet, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

4

**Chapter Title:**

Chemical Bonding and Molecular Structure

**Ncert Context:**

NCERT Class 12 Chemistry Ch.4: Ionic, covalent, and metallic bonds. VSEPR predicts geometry from electron pairs. Hybridisation sp, sp², sp³. Focus: Chemical Bonding and Molecular Structure exam prep.

**Concept:**

VSEPR theory

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **VSEPR theory** helps predict molecular geometry based on electron pairs.\n- **Electron pairs** include bonding and lone pairs that influence shape.\n- **Hybridisation** explains the mixing of atomic orbitals to form new hybrid orbitals.\n\n### Exam highlights\n- VSEPR theory is crucial for understanding molecular shapes and angles.\n- Common geometries include linear, trigonal planar, tetrahedral, and octahedral.\n- Remember the hybridisation types: sp (linear), sp² (trigonal planar), sp³ (tetrahedral).\n\n### Ask me for full clarity\n1. What specific molecular shapes are you struggling to remember?\n2. Do you need help with hybridisation concepts?\n3. Are there particular examples of VSEPR theory you want to discuss?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "VSEPR shapes quiz",
      "prompt": "Can you explain the different molecular shapes predicted by VSEPR theory?"
    },
    {
      "label": "Hybridisation types",
      "prompt": "What are the different types of hybridisation and their geometries?"
    },
    {
      "label": "Electron pairs role",
      "prompt": "How do bonding and lone pairs affect molecular geometry in VSEPR theory?"
    },
    {
      "label": "Common examples",
      "prompt": "What are some common examples of molecules that illustrate VSEPR theory?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards help memorize key terms and definitions related to VSEPR theory.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Quizzes test understanding of molecular shapes and hybridisation concepts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Mind maps can visually organize the relationships between different molecular geometries and hybridisation.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Slide decks can present VSEPR theory concepts in a structured format for revision.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `tutor_notebook_bootstrap-006`

- **Variation:** jee
- **Tags:** cbse, physics, tutor_mode, jee, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

3

**Chapter Title:**

Current Electricity

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR. Resistivity ρ=RA/L. Kirchhoff junction rule: ΣI_in=ΣI_out. Loop rule: ΣΔV=0. Wheatstone bridge for unknown R. Focus: Current Electricity exam prep.

**Concept:**

Kirchhoff's laws

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Ohm's Law**: The relationship between voltage, current, and resistance, expressed as V=IR.\n- **Kirchhoff's Junction Rule**: States that the total current entering a junction equals the total current leaving it (ΣI_in=ΣI_out).\n- **Kirchhoff's Loop Rule**: The sum of the potential differences (voltage) around any closed loop in a circuit is zero (ΣΔV=0).\n- **Wheatstone Bridge**: A method to determine an unknown resistance in a circuit.\n\n### Exam highlights\n- Remember Ohm's Law for calculations involving current, voltage, and resistance.\n- Kirchhoff's laws are essential for analyzing complex circuits; practice applying them in problems.\n- The Wheatstone bridge is particularly useful for measuring unknown resistances accurately.\n\n### Ask me for full clarity\n1. Can you explain Kirchhoff's Junction Rule in your own words?\n2. How would you apply Kirchhoff's Loop Rule to a simple circuit?\n3. What is the significance of the Wheatstone bridge in practical applications?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain Junction Rule",
      "prompt": "Can you explain Kirchhoff's Junction Rule in your own words?"
    },
    {
      "label": "Loop Rule Application",
      "prompt": "How would you apply Kirchhoff's Loop Rule to a simple circuit?"
    },
    {
      "label": "Wheatstone Bridge Use",
      "prompt": "What is the significance of the Wheatstone bridge in practical applications?"
    },
    {
      "label": "Ohm's Law Examples",
      "prompt": "Can you provide examples of problems using Ohm's Law?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Great for memorizing key terms and definitions related to Kirchhoff's laws.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Helps test understanding of Kirchhoff's laws and their applications.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Useful for visualizing the relationships between concepts in current electricity.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Effective for summarizing and presenting key concepts and formulas.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `tutor_notebook_bootstrap-007`

- **Variation:** multi_part
- **Tags:** cbse, chemistry, tutor_mode, multi_part, production_llm_gold

**Inputs**

**Class Num:**

11

**Subject Label:**

Chemistry

**Chapter No:**

7

**Chapter Title:**

Equilibrium

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants]. Le Chatelier: system opposes stress. Catalyst does not change K. Ionic equilibrium Ka, Kb, Kw. Focus: Equilibrium exam prep.

**Concept:**

Le Chatelier's principle

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Le Chatelier's Principle**: A system at equilibrium will shift to counteract any imposed change or stress.\n- **Equilibrium Constant (Kc)**: Defined as the ratio of the concentration of products to reactants at equilibrium.\n- **Catalysts**: They speed up the rate of reaching equilibrium but do not affect the equilibrium constant (K).\n- **Ionic Equilibrium**: Involves concepts like Ka, Kb, and Kw, which are crucial for understanding acid-base equilibria.\n\n### Exam highlights\n- Remember that Kc = [products]/[reactants] at equilibrium.\n- Le Chatelier's principle is essential for predicting the direction of shift in response to changes in concentration, temperature, and pressure.\n- Catalysts do not change the value of Kc.\n\n### Ask me for full clarity\n1. How does temperature affect the position of equilibrium according to Le Chatelier's principle?\n2. Can you explain the difference between Ka and Kb?\n3. What happens to the equilibrium position if the concentration of reactants is increased?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain Kc further",
      "prompt": "Can you explain how to calculate Kc for a given reaction in Chapter 7?"
    },
    {
      "label": "Le Chatelier's shifts",
      "prompt": "What are some examples of how Le Chatelier's principle applies to real-life situations?"
    },
    {
      "label": "Catalysts impact",
      "prompt": "How do catalysts influence the equilibrium position in chemical reactions?"
    },
    {
      "label": "Ionic equilibria",
      "prompt": "What is the significance of Ka, Kb, and Kw in ionic equilibrium?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards help reinforce key definitions and principles in equilibrium.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Quizzes can test understanding of concepts like Kc and Le Chatelier's principle.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Mind maps can visually organize the relationships between different types of equilibria.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Slide decks can summarize key concepts and provide visual aids for studying.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `tutor_notebook_bootstrap-008`

- **Variation:** conceptual
- **Tags:** cbse, biology, tutor_mode, conceptual, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Biology

**Chapter No:**

6

**Chapter Title:**

Molecular Basis of Inheritance

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA double helix A-T, G-C. Semiconservative replication. Central dogma: DNA→RNA→protein. Genetic code is triplet, degenerate. Focus: Molecular Basis of Inheritance exam prep.

**Concept:**

DNA replication

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **DNA double helix**: The structure of DNA consists of two strands forming a double helix, with complementary base pairing (A-T, G-C).\n- **Semiconservative replication**: During DNA replication, each new DNA molecule consists of one original and one new strand, ensuring genetic continuity.\n- **Central dogma**: The flow of genetic information follows the sequence DNA → RNA → protein, which is fundamental to molecular biology.\n- **Genetic code**: The genetic code is triplet and degenerate, meaning that multiple codons can code for the same amino acid.\n\n### Exam highlights\n- DNA replication is crucial for cell division and occurs during the S phase of the cell cycle.\n- Understanding the roles of enzymes like DNA polymerase in replication is essential for exam questions.\n- The concept of the central dogma is often tested; be clear on how it connects DNA, RNA, and protein synthesis.\n\n### Ask me for full clarity\n1. What specific aspects of DNA replication would you like to understand better?\n2. Are you clear on the roles of different enzymes involved in DNA replication?\n3. Do you need help with the implications of the central dogma in genetics?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain DNA structure",
      "prompt": "Can you explain the structure of DNA, focusing on the double helix and base pairing from Chapter 6?"
    },
    {
      "label": "Details on replication",
      "prompt": "What are the steps involved in semiconservative replication as described in Chapter 6?"
    },
    {
      "label": "Central dogma overview",
      "prompt": "Can you summarize the central dogma of molecular biology from Chapter 6?"
    },
    {
      "label": "Genetic code insights",
      "prompt": "What does it mean that the genetic code is triplet and degenerate according to Chapter 6?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Flashcards are great for memorizing key terms and definitions related to DNA replication.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz will help reinforce understanding of the processes involved in DNA replication.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can help visualize the connections between DNA structure, replication, and the central dogma.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "A slide deck can effectively present the key concepts and processes in a structured format.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `tutor_notebook_bootstrap-009`

- **Variation:** case_study
- **Tags:** cbse, civics-polity, tutor_mode, case_study, production_llm_gold

**Inputs**

**Class Num:**

10

**Subject Label:**

Civics

**Chapter No:**

3

**Chapter Title:**

Gender, Religion and Caste

**Ncert Context:**

NCERT Class 10 Civics Ch.3: Gender division is social, not biological. Secularism: state has no official religion. Caste inequalities persist; reservation policies. Focus: Gender, Religion and Caste exam prep.

**Concept:**



**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Gender division** is a social construct, emphasizing that it is shaped by societal norms rather than biology.\n- **Secularism** in India means that the state does not favor any religion, ensuring equality among all citizens.\n- **Caste inequalities** continue to exist in society, leading to the implementation of reservation policies to uplift marginalized communities.\n\n### Exam highlights\n- Gender division is not determined by biological differences but by social roles.\n- Secularism is crucial for maintaining harmony in a diverse nation like India.\n- Reservation policies aim to reduce caste-based inequalities in education and employment.\n\n### Ask me for full clarity\n1. What are the implications of gender division in society?\n2. How does secularism affect religious practices in India?\n3. Can you explain the impact of reservation policies on caste inequalities?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain gender division",
      "prompt": "Can you explain the concept of gender division in Chapter 3?"
    },
    {
      "label": "Discuss secularism",
      "prompt": "What does secularism mean in the context of Indian society as discussed in Chapter 3?"
    },
    {
      "label": "Caste inequalities",
      "prompt": "What are the main caste inequalities mentioned in Chapter 3 and their effects?"
    },
    {
      "label": "Reservation policies",
      "prompt": "How do reservation policies address caste inequalities as per Chapter 3?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "slide_deck",
      "reason": "A slide deck will help visualize key concepts and their interconnections.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "A quiz will reinforce understanding of the chapter's main ideas and facts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "A mind map can help organize and relate various concepts like gender, religion, and caste.",
      "auto_generate": false
    },
    {
      "type": "flashcards",
      "reason": "Flashcards can aid in memorizing key terms and definitions from the chapter.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `tutor_notebook_bootstrap-010`

- **Variation:** ncert_strict
- **Tags:** cbse, economics, tutor_mode, ncert_strict, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Economics

**Chapter No:**

2

**Chapter Title:**

National Income Accounting

**Ncert Context:**

NCERT Class 12 Economics Ch.2: GDP at market prices. GNP=GDP+NFIA. Circular flow of income. Depreciation deducted for NDP. Focus: National Income Accounting exam prep.

**Concept:**

GDP vs GNP

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **GDP**: Represents the total value of goods and services produced within a country's borders at market prices.\n- **GNP**: Measures the total income earned by a nation's residents, regardless of where the production occurs.\n- **NFIA**: Net Factor Income from Abroad, which adjusts GDP to calculate GNP.\n- **NDP**: Net Domestic Product, calculated by deducting depreciation from GDP.\n\n### Exam highlights\n- GNP = GDP + NFIA; this formula is crucial for understanding the difference between these two measures.\n- Remember that GDP focuses on location, while GNP focuses on ownership.\n\n### Ask me for full clarity\n1. What is the significance of NFIA in the calculation of GNP?\n2. Can you explain how depreciation affects the calculation of NDP?\n3. How do GDP and GNP reflect a country's economic health differently?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain GDP vs GNP",
      "prompt": "Can you explain the differences between GDP and GNP in detail?"
    },
    {
      "label": "Importance of NFIA",
      "prompt": "What role does Net Factor Income from Abroad (NFIA) play in calculating GNP?"
    },
    {
      "label": "Understanding NDP",
      "prompt": "How is Net Domestic Product (NDP) calculated from GDP?"
    },
    {
      "label": "Economic health indicators",
      "prompt": "How do GDP and GNP serve as indicators of economic health?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "mind_map",
      "reason": "Helps visualize the relationships between GDP, GNP, and NFIA.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Reinforces understanding of key concepts and formulas.",
      "auto_generate": true
    },
    {
      "type": "slide_deck",
      "reason": "Useful for summarizing and presenting key points effectively.",
      "auto_generate": false
    },
    {
      "type": "flashcards",
      "reason": "Good for memorizing definitions and formulas, but less critical here.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `typo`


#### Example 1: `tutor_notebook_bootstrap-011`

- **Variation:** typo
- **Tags:** cbse, physics, tutor_mode, typo, production_llm_gold

**Inputs**

**Class Num:**

11

**Subject Label:**

Physics

**Chapter No:**

7

**Chapter Title:**

Gravitation

**Ncert Context:**

NCERT Class 11 Physics Ch.7: Universal gravitation F=Gm₁m₂/r². g=GM/R². Kepler's laws for planetary motion. Escape velocity v_e=√(2gR). Focus: Gravitation exam prep.

**Concept:**

Kepler's laws

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Kepler's Laws**: These describe the motion of planets around the sun, including their elliptical orbits.\n- **Universal Gravitation**: The force of attraction between two masses, defined by the formula F=Gm₁m₂/r².\n- **Escape Velocity**: The minimum speed needed to break free from a celestial body's gravitational pull, given by v_e=√(2gR).\n- **Gravitational Field Strength**: The force per unit mass experienced by a small test mass in a gravitational field, represented as g=GM/R².\n\n### Exam highlights\n- Remember Kepler's three laws: 1) Orbits are ellipses, 2) Equal areas in equal times, 3) The square of the period is proportional to the cube of the semi-major axis.\n- Key formulas: F=Gm₁m₂/r², g=GM/R², and v_e=√(2gR).\n\n### Ask me for full clarity\n1. Can you explain the significance of each of Kepler's laws?\n2. How does the concept of escape velocity relate to gravitational force?\n3. What are the practical applications of understanding gravitation in real life?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Explain Kepler's Laws",
      "prompt": "Can you explain the significance of each of Kepler's laws in Chapter 7?"
    },
    {
      "label": "Discuss Escape Velocity",
      "prompt": "How does the concept of escape velocity relate to gravitational force in Chapter 7?"
    },
    {
      "label": "Gravitational Field Strength",
      "prompt": "What is the formula for gravitational field strength and its significance in Chapter 7?"
    },
    {
      "label": "Applications of Gravitation",
      "prompt": "What are the practical applications of understanding gravitation in real life from Chapter 7?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "flashcards",
      "reason": "Useful for memorizing key terms and formulas related to gravitation.",
      "auto_generate": true
    },
    {
      "type": "quiz",
      "reason": "Helps assess understanding of Kepler's laws and gravitational concepts.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "Visual representation of the relationships between concepts in gravitation.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "Effective for summarizing and presenting key ideas in a structured format.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `tutor_notebook_bootstrap-012`

- **Variation:** proof
- **Tags:** cbse, mathematics, tutor_mode, proof, production_llm_gold

**Inputs**

**Class Num:**

12

**Subject Label:**

Mathematics

**Chapter No:**

7

**Chapter Title:**

Integrals

**Ncert Context:**

NCERT Class 12 Maths Ch.7: ∫x^n dx=x^(n+1)/(n+1)+C, n≠-1. Fundamental theorem links definite integral to antiderivative. Area under curve. Focus: Integrals exam prep.

**Concept:**

Definite integrals

**Expected output**

**Bootstrap Json:**

```json
{
  "opening_summary": "## Summary\n\n### Key topics\n- **Definite integrals**: Understanding the concept of definite integrals and their applications in calculating area under curves.\n- **Fundamental theorem of calculus**: Links the concept of antiderivatives to definite integrals, providing a method to evaluate them.\n- **Area under the curve**: Using definite integrals to find the area between the curve and the x-axis over a specific interval.\n\n### Exam highlights\n- The formula for definite integrals is derived from the antiderivative: ∫[a to b] f(x) dx = F(b) - F(a), where F is an antiderivative of f.\n- Remember that the integral of x^n is given by ∫x^n dx = x^(n+1)/(n+1) + C, for n ≠ -1.\n\n### Ask me for full clarity\n1. What specific areas of definite integrals do you find challenging?\n2. Do you need help with the fundamental theorem of calculus?\n3. Would you like to practice problems related to area under curves?\n\nTap a suggestion below or ask your own question.",
  "suggestions": [
    {
      "label": "Definite integrals basics",
      "prompt": "Can you explain the basics of definite integrals in Chapter 7?"
    },
    {
      "label": "Fundamental theorem",
      "prompt": "What is the fundamental theorem of calculus and how does it relate to definite integrals?"
    },
    {
      "label": "Area under curve",
      "prompt": "How do you calculate the area under a curve using definite integrals?"
    },
    {
      "label": "Example problems",
      "prompt": "Can you provide example problems on definite integrals from Chapter 7?"
    }
  ],
  "studio_recommendations": [
    {
      "type": "quiz",
      "reason": "To practice problem-solving skills related to definite integrals.",
      "auto_generate": true
    },
    {
      "type": "flashcards",
      "reason": "To reinforce key definitions and formulas related to definite integrals.",
      "auto_generate": true
    },
    {
      "type": "mind_map",
      "reason": "To visualize the connections between concepts in Chapter 7.",
      "auto_generate": false
    },
    {
      "type": "slide_deck",
      "reason": "To summarize and present the key concepts of definite integrals.",
      "auto_generate": false
    }
  ]
}
```

**Quality Check:** opening_structure: pass. suggestions_unique: pass. studio_pair: pass. ncert_grounding: pass. production_llm_gold: pass.

---


## 24. Tutor Follow-up Questions Agent

| Field | Value |
|-------|-------|
| Dataset ID | `tutor_follow_up_questions` |
| Category | Tutor Mode |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** After each tutor exchange, suggest exactly three follow-up questions (≤90 chars) mixing clarify/deepen, apply/practice, and exam-angle. Production: [`tutor/follow_up_questions.j2`](packages/core/prompts/templates/tutor/follow_up_questions.j2).

**Audit finding (baseline v1.0.0):** Baseline v1.0.0 recycled generic templates with easy definitional exchanges. v1.5.0 rebuilds medium-difficulty multi-step exchanges, aligned scope, and production LLM gold.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `typo` | Student typo tolerance | 3 |
| `conversational` | Natural follow-ups | 4 |
| `diagram` | Post diagram explanation | 3 |
| `cbse` | Board exam angle | 3 |
| `neet` | NEET drill | 3 |
| `jee` | JEE application | 3 |
| `multi_part` | Multi-step topic | 2 |
| `conceptual` | Deepen understanding | 3 |
| `case_study` | Civics/social apply | 2 |
| `ncert_strict` | Strict NCERT tie-in | 2 |
| `proof` | Math reasoning | 2 |
| `edge_not_found` | RAG miss recovery | 1 |
| `numerical` | Numeric practice | 1 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **three_follow_ups** — Exactly 3 questions, each ≤90 characters.
* **specificity** — No generic 'Tell me more'; tied to last exchange.
* **mix_roles** — Clarify, apply/practice, and exam-angle present.
* **scope_alignment** — Chapter title and subject match exchange content.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `user_message`, `assistant_message`, `class_num`, `subject_label`, `chapter_no`, `chapter_title`, `concept`
* Output keys: `follow_ups`

**Prompt template (production):**

```jinja2
You are ScholarSync Tutor. Given the student's scope and the last exchange, suggest follow-up questions that give **directionality** — deeper understanding, application, exam prep, or fixing misconceptions.

## Scope
Class {{ class_num }} · {{ subject_label }} · Ch. {{ chapter_no }} {{ chapter_title }}
{% if concept %}Concept: {{ concept }}{% endif %}

## Last exchange
Student: {{ user_message }}
Tutor: {{ assistant_message }}

## Rules
- Return JSON only: {"follow_ups": ["...", "...", "..."]}
- Exactly 3 questions, each ≤90 characters
- Must be **specific** to what was just discussed (no generic "Tell me more")
- Mix: 1 clarify/deepen, 1 apply/practice, 1 connect/exam-angle
- Student tone; no teacher jargon
- Do not repeat the student's exact question
- If assistant said "Not found in provided sources", suggest rephrases or related NCERT subtopics instead
```

*Runtime note:* `TutorNotebookBootstrapService.generate_follow_ups()` after tutor chat turn.

### Evaluation examples (30)
## Variation: `typo`


#### Example 1: `tutor_follow_up_questions-001`

- **Variation:** typo
- **Tags:** cbse, science, typo, production_llm_gold

**Inputs**

**User Message:**

In a series circuit with two 4Ω resistors and a 12V battery, why is current the same through both resistors but voltage splits?

**Assistant Message:**

In series, charge has one path so current I is identical. Each resistor drops V=IR; total 12V splits as 4I + 4I = 8I, giving I = 1.5 A.

**Class Num:**

10

**Subject Label:**

Science

**Chapter No:**

12

**Chapter Title:**

Electricity

**Concept:**

Ohm's law

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "What happens to current if one resistor is removed from the circuit?",
    "Can you calculate voltage drop across each resistor with 1.5 A current?",
    "How would this change if the resistors were in parallel instead?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-011`

- **Variation:** typo
- **Tags:** cbse, physics, typo, production_llm_gold

**Inputs**

**User Message:**

Why does escape velocity depend on planet radius and g but not on the mass of the escaping object?

**Assistant Message:**

Escape speed balances kinetic and gravitational potential per unit mass: ½v² = GM/R. The object's mass cancels; only the field strength at the surface matters.

**Class Num:**

11

**Subject Label:**

Physics

**Chapter No:**

7

**Chapter Title:**

Gravitation

**Concept:**

Kepler's laws

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain how g changes with altitude and its effect on escape velocity?",
    "How would you calculate escape velocity for a planet with double the radius?",
    "What might be a common mistake when applying Kepler's laws in exam questions?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `conversational`


#### Example 1: `tutor_follow_up_questions-002`

- **Variation:** conversational
- **Tags:** cbse, biology, conversational, production_llm_gold

**Inputs**

**User Message:**

How does gastric pH affect pepsinogen activation, and what happens if antacid raises stomach pH too much?

**Assistant Message:**

HCl converts pepsinogen to active pepsin near pH 2. Excess antacid raises pH, reducing pepsin activity and slowing protein digestion in the stomach.

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

16

**Chapter Title:**

Digestion and Absorption

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "What are the consequences of low gastric pH on digestion?",
    "Can you explain how pepsin works on proteins?",
    "How might this topic appear in exam questions on digestion?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-013`

- **Variation:** conversational
- **Tags:** cbse, geography, conversational, production_llm_gold

**Inputs**

**User Message:**

If contour ploughing reduces erosion on slopes, why might terrace farming be needed on steeper hills?

**Assistant Message:**

Contour ploughing slows runoff on moderate slopes. Steeper gradients still concentrate water; terraces break slope length and reduce velocity before soil is washed away.

**Class Num:**

10

**Subject Label:**

Geography

**Chapter No:**

1

**Chapter Title:**

Resources and Development

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How do terraces help with water retention on steep hills?",
    "Can you explain how contour ploughing works in detail?",
    "What are the advantages of terrace farming in exam questions?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 3: `tutor_follow_up_questions-027`

- **Variation:** conversational
- **Tags:** cbse, mathematics, conversational, production_llm_gold

**Inputs**

**User Message:**

Why can afforestation reduce soil erosion but not fix salinisation caused by over-irrigation?

**Assistant Message:**

Tree cover cuts wind and water erosion by binding soil. Salinisation needs drainage and better irrigation scheduling; roots alone cannot leach accumulated salts from the root zone.

**Class Num:**

12

**Subject Label:**

Mathematics

**Chapter No:**

7

**Chapter Title:**

Integrals

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does tree cover specifically reduce wind erosion?",
    "Can you think of a real-life example of afforestation helping soil?",
    "What are key points on salinisation for exam prep?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `tutor_follow_up_questions-003`

- **Variation:** diagram
- **Tags:** cbse, physics, diagram, production_llm_gold

**Inputs**

**User Message:**

For a convex lens with u = −30 cm and f = +15 cm, why must we use the sign convention before applying 1/f = 1/v − 1/u?

**Assistant Message:**

Real objects are on the incoming-light side, so u is negative. Using magnitudes without signs gives wrong v and mislabels image as real or virtual.

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

9

**Chapter Title:**

Ray Optics and Optical Instruments

**Concept:**

Lens formula

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does the sign convention change for concave lenses?",
    "Can you calculate v for u = -30 cm using the lens formula?",
    "Why is it important to identify real vs virtual images in exams?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-014`

- **Variation:** diagram
- **Tags:** cbse, biology, diagram, production_llm_gold

**Inputs**

**User Message:**

In C₄ plants, why is the Calvin cycle still in bundle-sheath cells if initial CO₂ fixation happens in mesophyll?

**Assistant Message:**

Mesophyll cells fix CO₂ into a 4-carbon acid that shuttles to bundle sheath, where CO₂ is released internally, raising local concentration and cutting photorespiration.

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

13

**Chapter Title:**

Photosynthesis in Higher Plants

**Concept:**

Calvin cycle

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does the CO₂ concentration affect the efficiency of photosynthesis?",
    "Can you explain how C₄ plants adapt to hot environments using the Calvin cycle?",
    "What exam questions might ask about the role of bundle-sheath cells in C₄ plants?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 3: `tutor_follow_up_questions-028`

- **Variation:** diagram
- **Tags:** cbse, geography, diagram, production_llm_gold

**Inputs**

**User Message:**

In hot climates, why do C₄ plants outperform C₃ plants even though both use the Calvin cycle?

**Assistant Message:**

C₄ concentrates CO₂ before Calvin cycle, keeping RuBisCO on carboxylation and lowering photorespiration when stomata close to reduce water loss in heat.

**Class Num:**

10

**Subject Label:**

Geography

**Chapter No:**

1

**Chapter Title:**

Resources and Development

**Concept:**

Calvin cycle

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain how photorespiration affects plant growth in different climates?",
    "How would you compare the water use efficiency of C₄ and C₃ plants in agriculture?",
    "What exam questions might ask about the advantages of C₄ plants in hot climates?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `tutor_follow_up_questions-004`

- **Variation:** cbse
- **Tags:** cbse, mathematics, cbse, production_llm_gold

**Inputs**

**User Message:**

If a quadratic has D = 0 but coefficients are not proportional to a perfect square, how do we still know roots are equal?

**Assistant Message:**

D = b² − 4ac = 0 means the quadratic touches the x-axis once. The repeated root is −b/(2a), even if factorisation is not obvious.

**Class Num:**

10

**Subject Label:**

Mathematics

**Chapter No:**

4

**Chapter Title:**

Quadratic Equations

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain why D = 0 guarantees equal roots?",
    "Can you find the roots of a quadratic with D = 0?",
    "How might this concept show up in your exams?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-016`

- **Variation:** cbse
- **Tags:** cbse, science, cbse, production_llm_gold

**Inputs**

**User Message:**

Three identical resistors in parallel share 12 V. Why is branch current I/3 but total power not simply P/3?

**Assistant Message:**

Each resistor gets full 12 V, so each dissipates V²/R. Three paths triple total current and total power becomes 3V²/R, not one-third of a single resistor's power.

**Class Num:**

10

**Subject Label:**

Science

**Chapter No:**

12

**Chapter Title:**

Electricity

**Concept:**

Ohm's law

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain how total current is calculated in parallel circuits?",
    "What happens to power if one resistor is removed from the parallel setup?",
    "How would you solve a problem with different resistor values in parallel?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `tutor_follow_up_questions-005`

- **Variation:** neet
- **Tags:** cbse, chemistry, neet, production_llm_gold

**Inputs**

**User Message:**

Why does NH₃ have pyramidal geometry while BF₃ is trigonal planar despite both having three bonded atoms?

**Assistant Message:**

NH₃ has one lone pair on nitrogen; four electron domains → tetrahedral electron geometry, pyramidal shape. BF₃ has three domains only → trigonal planar.

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

4

**Chapter Title:**

Chemical Bonding and Molecular Structure

**Concept:**

VSEPR theory

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does lone pair repulsion affect molecular shape?",
    "Can you predict the shape of H₂O using VSEPR?",
    "What geometry would a molecule with 4 bonded atoms and no lone pairs have?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-017`

- **Variation:** neet
- **Tags:** cbse, biology, neet, production_llm_gold

**Inputs**

**User Message:**

Why does trypsin act in the alkaline duodenum but not in the acidic stomach?

**Assistant Message:**

Trypsin is secreted as inactive trypsinogen and needs enterokinase and pH ~8. Gastric HCl would denature or fail to activate it, so activity is localised to the small intestine.

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

16

**Chapter Title:**

Digestion and Absorption

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "What role does enterokinase play in activating trypsinogen?",
    "Can you explain why pH affects enzyme activity using other examples?",
    "How might this knowledge help with exam questions on enzyme functions?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 3: `tutor_follow_up_questions-020`

- **Variation:** neet
- **Tags:** cbse, chemistry, neet, production_llm_gold

**Inputs**

**User Message:**

Why is sp³ hybridisation in methane consistent with four equivalent C−H bonds, not three bonds plus one lone pair?

**Assistant Message:**

Carbon promotes one 2s electron to 3p, mixes to four sp³ orbitals. Each overlaps with H 1s, giving four identical σ bonds and tetrahedral 109.5° angles.

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

4

**Chapter Title:**

Chemical Bonding and Molecular Structure

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does hybridization affect bond angles in other molecules?",
    "Can you draw the Lewis structure for methane and show hybridization?",
    "Why is tetrahedral shape important in predicting molecular properties?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `tutor_follow_up_questions-006`

- **Variation:** jee
- **Tags:** cbse, physics, jee, production_llm_gold

**Inputs**

**User Message:**

In a Wheatstone bridge, why can't we apply the loop rule to only one branch when finding the unknown resistor?

**Assistant Message:**

Kirchhoff's loop rule needs a closed path with consistent sign for each IR drop. A single branch is not a closed loop, so ΣΔV = 0 cannot be applied there alone.

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

3

**Chapter Title:**

Current Electricity

**Concept:**

Kirchhoff's laws

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain how to apply the loop rule in a full Wheatstone bridge?",
    "How would you calculate the unknown resistor using Kirchhoff's laws?",
    "What exam problems involve Kirchhoff's laws that you find tricky?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-018`

- **Variation:** jee
- **Tags:** cbse, physics, jee, production_llm_gold

**Inputs**

**User Message:**

For total internal reflection, why is the critical angle defined only when light goes from denser to rarer medium?

**Assistant Message:**

TIR needs the refracted ray bent beyond 90°. That happens when n₁ sin i = n₂ sin r cannot be solved for real r with n₁ > n₂ beyond the critical angle.

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

9

**Chapter Title:**

Ray Optics and Optical Instruments

**Concept:**

Lens formula

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain what happens at angles greater than the critical angle?",
    "How would you calculate the critical angle for water to air?",
    "Why is TIR important in optical fibers for communication?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 3: `tutor_follow_up_questions-025`

- **Variation:** jee
- **Tags:** cbse, economics, jee, production_llm_gold

**Inputs**

**User Message:**

Using Kepler's third law, why do planets farther from the Sun have longer years but not necessarily lower orbital speed?

**Assistant Message:**

T² ∝ r³ gives longer periods, but v ≈ √(GM/r) decreases only as 1/√r. Outer planets move slower, yet the much longer path increases the year dramatically.

**Class Num:**

12

**Subject Label:**

Economics

**Chapter No:**

2

**Chapter Title:**

National Income Accounting

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does the mass of the Sun affect planetary speeds and periods?",
    "Can you calculate the orbital speed of a planet at a specific distance from the Sun?",
    "What implications does Kepler's law have for satellite orbits around Earth?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `tutor_follow_up_questions-007`

- **Variation:** multi_part
- **Tags:** cbse, chemistry, multi_part, production_llm_gold

**Inputs**

**User Message:**

If we add an inert gas at constant volume to an equilibrium A ⇌ B, does Q change or only total pressure?

**Assistant Message:**

At constant V, partial pressures of A and B are unchanged, so Q = [B]/[A] stays the same. Equilibrium position does not shift; only total P rises.

**Class Num:**

11

**Subject Label:**

Chemistry

**Chapter No:**

7

**Chapter Title:**

Equilibrium

**Concept:**

Le Chatelier's principle

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does adding a gas at constant pressure affect equilibrium?",
    "Can you explain how temperature changes influence Q?",
    "What might be a typical exam question on Le Chatelier's principle?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-021`

- **Variation:** multi_part
- **Tags:** cbse, physics, multi_part, production_llm_gold

**Inputs**

**User Message:**

In a balanced Wheatstone bridge, why is the galvanometer current zero even though P and Q carry different currents?

**Assistant Message:**

At balance, potential at the midpoints of both arms is equal, so no PD across the galvanometer. Current divides in the arms but the junction potentials match.

**Class Num:**

12

**Subject Label:**

Physics

**Chapter No:**

3

**Chapter Title:**

Current Electricity

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does changing resistance in one arm affect the balance?",
    "Can you calculate the current in each arm with specific values?",
    "What exam questions might involve Wheatstone bridge concepts?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `tutor_follow_up_questions-008`

- **Variation:** conceptual
- **Tags:** cbse, biology, conceptual, production_llm_gold

**Inputs**

**User Message:**

During DNA replication, why is the leading strand continuous but the lagging strand made of Okazaki fragments?

**Assistant Message:**

DNA polymerase moves 5′→3′. At the fork, one template strand runs 3′→5′ relative to synthesis, forcing discontinuous short fragments on the lagging side.

**Class Num:**

12

**Subject Label:**

Biology

**Chapter No:**

6

**Chapter Title:**

Molecular Basis of Inheritance

**Concept:**

DNA replication

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain why DNA polymerase can only add nucleotides in one direction?",
    "How would you describe the process of joining Okazaki fragments after replication?",
    "What might happen if Okazaki fragments weren't properly joined during DNA replication?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-022`

- **Variation:** conceptual
- **Tags:** cbse, chemistry, conceptual, production_llm_gold

**Inputs**

**User Message:**

Why is the genetic code called degenerate if each codon still codes for only one amino acid?

**Assistant Message:**

Degenerate means multiple codons can specify the same amino acid (e.g. leucine has six). It does not mean one codon maps to many amino acids—that would break translation fidelity.

**Class Num:**

11

**Subject Label:**

Chemistry

**Chapter No:**

7

**Chapter Title:**

Equilibrium

**Concept:**

DNA replication

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain why fidelity is crucial in DNA translation?",
    "How would a mutation in a codon affect protein synthesis?",
    "What role does degenerate coding play in genetic diversity?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `tutor_follow_up_questions-009`

- **Variation:** case_study
- **Tags:** cbse, civics-polity, case_study, production_llm_gold

**Inputs**

**User Message:**

How can caste-based mobilisation both strengthen democracy and deepen social divisions at the same time?

**Assistant Message:**

It increases political participation and representation of marginal groups, but can also harden identity voting and reduce cross-community coalitions on policy issues.

**Class Num:**

10

**Subject Label:**

Civics

**Chapter No:**

3

**Chapter Title:**

Gender, Religion and Caste

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you give examples of how caste affects voting patterns in elections?",
    "How might caste-based mobilization impact policy decisions in local governance?",
    "What are the potential exam questions on caste and democracy you can think of?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-023`

- **Variation:** case_study
- **Tags:** cbse, biology, case_study, production_llm_gold

**Inputs**

**User Message:**

How does Indian secularism differ from Western separation when the state funds religious schools and personal laws coexist?

**Assistant Message:**

Indian secularism emphasises equal respect and principled distance, not strict church–state separation. The state may reform personal laws and subsidise education without adopting a state religion.

**Class Num:**

12

**Subject Label:**

Biology

**Chapter No:**

6

**Chapter Title:**

Molecular Basis of Inheritance

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "What are examples of personal laws in India that reflect this approach?",
    "How might funding religious schools impact social equality in India?",
    "Can you compare this to secularism in another country for your exam?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `tutor_follow_up_questions-010`

- **Variation:** ncert_strict
- **Tags:** cbse, economics, ncert_strict, production_llm_gold

**Inputs**

**User Message:**

Why is GDP at market prices not the same as national income, and where does depreciation enter?

**Assistant Message:**

National income (NNP at factor cost) adjusts GDP for net indirect taxes and depreciation. Ignoring depreciation overstates income available for consumption and investment.

**Class Num:**

12

**Subject Label:**

Economics

**Chapter No:**

2

**Chapter Title:**

National Income Accounting

**Concept:**

GDP vs GNP

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does depreciation affect GDP calculations over time?",
    "Can you give an example of net indirect taxes in GDP?",
    "Why is understanding NNP important for exam questions on income?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-024`

- **Variation:** ncert_strict
- **Tags:** cbse, civics-polity, ncert_strict, production_llm_gold

**Inputs**

**User Message:**

If NFIA is positive, does GNP exceed GDP or fall below it, and what does that imply about net factor income abroad?

**Assistant Message:**

GNP = GDP + NFIA. Positive NFIA means residents earn more abroad than foreigners earn domestically, so GNP > GDP.

**Class Num:**

10

**Subject Label:**

Civics

**Chapter No:**

3

**Chapter Title:**

Gender, Religion and Caste

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain why NFIA affects GNP and GDP differently?",
    "How would you calculate GNP if NFIA changes to negative?",
    "What impact does GNP have on a country's economic health in exams?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `tutor_follow_up_questions-012`

- **Variation:** proof
- **Tags:** cbse, mathematics, proof, production_llm_gold

**Inputs**

**User Message:**

For ∫₀¹ x√(1−x²) dx, why is substitution u = 1−x² more natural than integration by parts?

**Assistant Message:**

The derivative of 1−x² is −2x, matching the x factor outside the root. Parts would couple x with arcsin-type terms and add unnecessary steps.

**Class Num:**

12

**Subject Label:**

Mathematics

**Chapter No:**

7

**Chapter Title:**

Integrals

**Concept:**

Definite integrals

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does the substitution simplify the integral's evaluation?",
    "Can you try a similar integral using u = 1-x²?",
    "Why is substitution often preferred in definite integrals on exams?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-026`

- **Variation:** proof
- **Tags:** cbse, physics, proof, production_llm_gold

**Inputs**

**User Message:**

To prove ∫ₐᵇ f(x) dx = F(b) − F(a), what must we show about F beyond finding an antiderivative?

**Assistant Message:**

F must be continuous on [a,b] and differentiable with F′(x)=f(x) almost everywhere on the interval. The FTC links accumulation to net change of that antiderivative.

**Class Num:**

11

**Subject Label:**

Physics

**Chapter No:**

7

**Chapter Title:**

Gravitation

**Concept:**

Definite integrals

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does continuity of F affect the integral's value?",
    "Can you find an example where F is not continuous?",
    "What role does this play in exam questions on the FTC?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `edge_not_found`


#### Example 1: `tutor_follow_up_questions-029`

- **Variation:** edge_not_found
- **Tags:** cbse, biology, edge_not_found, production_llm_gold

**Inputs**

**User Message:**

Not found in provided sources for Nernst equation worked example at non-standard concentrations.

**Assistant Message:**

Not found in provided sources for this question.

**Class Num:**

11

**Subject Label:**

Biology

**Chapter No:**

13

**Chapter Title:**

Photosynthesis in Higher Plants

**Concept:**

Nernst equation

**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain how concentration affects the Nernst equation?",
    "How would you calculate the equilibrium potential at different ion concentrations?",
    "What role does the Nernst equation play in understanding photosynthesis?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

## Variation: `numerical`


#### Example 1: `tutor_follow_up_questions-015`

- **Variation:** numerical
- **Tags:** cbse, chemistry, numerical, production_llm_gold

**Inputs**

**User Message:**

For a galvanic cell with E°cell = +0.76 V, how do we use the Nernst equation when [Zn²⁺] doubles at 298 K?

**Assistant Message:**

Write Q from the cell reaction, then E = E° − (0.0591/n) log Q. Changing [Zn²⁺] alters Q and therefore the cell EMF from standard conditions.

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

3

**Chapter Title:**

Electrochemistry

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "What happens to E when [Zn²⁺] decreases instead of doubling?",
    "Can you calculate E for [Zn²⁺] = 0.1 M using the Nernst equation?",
    "How might this concept appear in your upcoming exam questions?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 2: `tutor_follow_up_questions-019`

- **Variation:** numerical
- **Tags:** cbse, mathematics, numerical, production_llm_gold

**Inputs**

**User Message:**

Without solving x² − 5x + 6 = 0, how can sum and product of roots verify the factorisation (x−2)(x−3)?

**Assistant Message:**

For ax²+bx+c, sum = −b/a = 5 and product = c/a = 6. If roots are 2 and 3, both checks match, confirming the factorisation without expansion errors.

**Class Num:**

10

**Subject Label:**

Mathematics

**Chapter No:**

4

**Chapter Title:**

Quadratic Equations

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "Can you explain why the sum and product formulas work for any quadratic?",
    "How would you apply these concepts to a different quadratic equation?",
    "What types of questions about roots might come up on your exam?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---

#### Example 3: `tutor_follow_up_questions-030`

- **Variation:** numerical
- **Tags:** cbse, chemistry, numerical, production_llm_gold

**Inputs**

**User Message:**

For a projectile launched at 45° on level ground, why is range maximum at 45° only when air resistance is neglected?

**Assistant Message:**

R = u²sin2θ/g assumes level ground and no drag. With air resistance, optimal angle shifts below 45° because horizontal speed decays faster than in the vacuum model.

**Class Num:**

12

**Subject Label:**

Chemistry

**Chapter No:**

3

**Chapter Title:**

Electrochemistry

**Concept:**



**Expected output**

**Follow Ups:**

```json
{
  "follow_ups": [
    "How does air resistance affect the trajectory of a projectile?",
    "Can you calculate the range for different angles with drag?",
    "Why is the 45° angle ideal in a vacuum for maximum range?"
  ]
}
```

**Quality Check:** three_follow_ups: pass. specificity: pass. mix_roles: pass. scope_alignment: pass. production_llm_gold: pass.

---


## 25. Source Question Extraction Agent

| Field | Value |
|-------|-------|
| Dataset ID | `source_question_extraction` |
| Category | Source Upload |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Parse uploaded exam/homework PDF text into structured question sections with previews, fullText, and confidence. Production: [`source_questions/extract.j2`](packages/core/prompts/templates/source_questions/extract.j2) via `SourceQuestionExtractionService`.

**Audit finding (baseline v1.0.0):** Baseline v1.0.0 returned identical wrong gold ('Define Ohm's law') for every input including NEET/JEE papers. Rebuilt with real Problem solver_Questions page extracts plus curated CBSE/NEET/JEE snippets and production LLM gold normalized through `_normalize_sections()`.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `mcq_section` | Sectioned CBSE/NEET MCQ papers | 8 |
| `numerical` | Numeric JEE/CBSE problems | 6 |
| `assertion_reason` | Assertion-reason blocks | 2 |
| `multi_section` | Multiple labeled sections | 3 |
| `footer_noise` | Headers/footers to ignore | 4 |
| `diagram_ref` | Figure-referenced stems | 3 |
| `case_study` | Passage-based questions | 2 |
| `multi_part` | Sub-part (a)(b) questions | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **question_count** — All numbered questions in document_text captured.
* **full_text_complete** — fullText sufficient to solve; preview ≤120 chars.
* **no_hallucination** — No invented questions beyond document_text.
* **confidence_calibration** — low confidence when boundaries uncertain.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `document_text`
* Output keys: `sections_json`

**Prompt template (production):**

```jinja2
You are an expert at parsing exam and homework question papers.

Given the raw text extracted from a PDF or image, identify every distinct question the student is expected to solve.

Return **only** valid JSON with this shape:
{
  "sections": [
    {
      "label": "Section A",
      "questions": [
        {
          "number": 1,
          "preview": "Short 1-2 line preview (max 120 chars)",
          "fullText": "Complete question text including sub-parts",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}

Rules:
- Include every numbered question you can find; do not invent questions.
- `preview` must be at most 120 characters.
- `fullText` must contain the full wording needed to solve the problem.
- Use `confidence: "low"` when numbering or boundaries are uncertain.
- If there are no section headers, use a single section with `"label": null`.
- Ignore answer keys, instructions-only pages, and headers/footers.
- Preserve math notation as plain text or LaTeX when present.

Document text:
{{ document_text }}
```

*Runtime note:* `SourceQuestionExtractionService.extract_questions()` on uploaded PDF/image sources.

### Evaluation examples (30)
## Variation: `mcq_section`


#### Example 1: `source_question_extraction-001`

- **Variation:** mcq_section
- **Tags:** cbse, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

Mathematics Board Testing Question Bank
3
Q18. Find the vector equation of a line passing through the origin and perpendicular to both the
lines r = 2i - j + 2k + λ(3i + 4j + 2k) and r = μ(i - j + k).
Q19. Vectors a = 3i - 2j + 2k and b = i + 2k represent the two adjacent sides of a
parallelogram. Find the vectors representing its diagonals and hence find their lengths.
Q20. The area of the circle is increasing at a uniform rate of 2 cm²/sec. How fast is the
circumference of the circle increasin

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 18,
          "preview": "Find the vector equation of a line through the origin.",
          "fullText": "Find the vector equation of a line passing through the origin and perpendicular to both the lines r = 2i - j + 2k + λ(3i + 4j + 2k) and r = μ(i - j + k).",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 19,
          "preview": "Find vectors representing diagonals of a parallelogram.",
          "fullText": "Vectors a = 3i - 2j + 2k and b = i + 2k represent the two adjacent sides of a parallelogram. Find the vectors representing its diagonals and hence find their lengths.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 20,
          "preview": "How fast is the circumference of the circle increasing?",
          "fullText": "The area of the circle is increasing at a uniform rate of 2 cm²/sec. How fast is the circumference of the circle increasing?",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-002`

- **Variation:** mcq_section
- **Tags:** cbse, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

Mathematics Board Testing Question Bank
2
Q8. The common region determined by all the constraints of a linear programming problem is
called:
(A) an unbounded region
(B) an optimal region
(C) a bounded region
(D) a feasible region
Q9. If A = [ -1 0 0 ; 0 1 0 ; 0 0 1 ], then A⁻¹ is:
(A) [ -1 0 0 ; 0 -1 0 ; 0 0 -1 ]
(B) [ 1 0 0 ; 0 -1 0 ; 0 0 -1 ]
(C) [ -1 0 0 ; 0 -1 0 ; 0 0 1 ]
(D) [ -1 0 0 ; 0 1 0 ; 0 0 1 ]
Q10. If d/dx (f(x)) = log x, then f(x) equals:
(A) -1/x + C
(B) x(log x - 1) + C
(C) x(log

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 8,
          "preview": "Identify the common region in linear programming.",
          "fullText": "The common region determined by all the constraints of a linear programming problem is called:\n(A) an unbounded region\n(B) an optimal region\n(C) a bounded region\n(D) a feasible region",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 9,
          "preview": "Find the inverse of matrix A.",
          "fullText": "If A = [ -1 0 0 ; 0 1 0 ; 0 0 1 ], then A⁻¹ is:\n(A) [ -1 0 0 ; 0 -1 0 ; 0 0 -1 ]\n(B) [ 1 0 0 ; 0 -1 0 ; 0 0 -1 ]\n(C) [ -1 0 0 ; 0 -1 0 ; 0 0 1 ]\n(D) [ -1 0 0 ; 0 1 0 ; 0 0 1 ]",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 10,
          "preview": "Determine the function f(x) given its derivative.",
          "fullText": "If d/dx (f(x)) = log x, then f(x) equals:\n(A) -1/x + C\n(B) x(log x - 1) + C\n(C) x(log",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `source_question_extraction-004`

- **Variation:** mcq_section
- **Tags:** cbse, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 6
SECTION B — Very Short Answer Questions (VSAQs)
Each question carries 2 marks. Answer briefly.
Q17. (a) Define humoral immune response.
(b) Name any two types of antibodies found to give humoral immune response in
humans.
Q18. (a) (i) How does a farmer use dormancy of seed to his advantage?
(ii) Differentiate between pea seed and castor seed.
OR
(b) Identify the stage of follicle where primary oocyte undergoes first meiotic division.
Also men

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section B",
      "questions": [
        {
          "number": 17,
          "preview": "Define humoral immune response and name two types of antibodies.",
          "fullText": "(a) Define humoral immune response.\n(b) Name any two types of antibodies found to give humoral immune response in humans.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 18,
          "preview": "Discuss seed dormancy and differentiate between two seed types.",
          "fullText": "(a) (i) How does a farmer use dormancy of seed to his advantage?\n(ii) Differentiate between pea seed and castor seed.\nOR\n(b) Identify the stage of follicle where primary oocyte undergoes first meiotic division.",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `source_question_extraction-016`

- **Variation:** mcq_section
- **Tags:** jee, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

Q35.
Two closed vessels of same volume are joined through a narrow tube and both vessels are filled with air of pressure
 kPa and temperature 
 K. Keeping the temperature of one vessel constant at 
 K the second vessel
temperature is raised to 
 K. The final pressure in the vessels is _______ kPa.
(1)
(2)
(3)
(4)
Q36.
In interference experiment the path difference between two interfering waves at a point  on the screen is 
,
where  is the wavelength of these waves, and at another point  the path

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 63,
          "preview": "Determine the oxidation state of chromium in a reaction.",
          "fullText": "The oxidation state of chromium in the final product formed in the reaction between KI and acidified K2Cr2O7 solution is: 1. +3 2. +6 3. +2 4. +4",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 64,
          "preview": "Identify the correct statement for generating a positive cell potential.",
          "fullText": "Consider the above electrochemical cell where a metal electrode (M) is undergoing redox reaction by forming M^+ (M → M^+ + e^−). The cation M^+ is present in two different concentrations c1 and c2 as shown above. Which of the following statement is correct for generating a positive cell potential?",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 5: `source_question_extraction-017`

- **Variation:** mcq_section
- **Tags:** jee, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

Q48.
The energy released when 
 kg of 
 is converted into 
 by proton bombardment is 
 eV. The value
of  is _______. (Nearest integer) (Mass of 
 u, mass of 
 u, mass of proton 
 u and
 u 
 MeV/c  and Avogadro number 
)
Q49.
A three coulomb charge moves from the point 
 to the point 
 in an electric field expressed as
 N/C. The work done in moving the charge is _______ J.
Q50.
A certain gas is isothermally compressed to 
 of its initial volume (
 litre) by applying required
pressure. If the bulk

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 51,
          "preview": "Evaluate the truth of two chemical synthesis statements.",
          "fullText": "Given below are two statements: Statement I: NH₂ CH₃ Cl C₂H₅ can be synthesized from using simpler reagents in the order i) Acidic KMnO₄, ii) Ammonia, iii) Bromine and alkali. Statement II: C₆H₅ Br can be converted into using reagents in the order i) Bromine-H₂O ii) NaNO₂/HCl (0 - 5 °C) iii) Aq. H₃PO₂. In the light of the above statements, choose the correct answer from the options given below 1. Statement I is false but Statement II is true 2. Both Statement I",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 6: `source_question_extraction-019`

- **Variation:** mcq_section
- **Tags:** neet, source_upload, mcq_section, production_llm_gold

**Inputs**

**Document Text:**

Q8.
Which micronutrient is required for splitting of water molecule during photosynthesis?
a. copper
b. manganese
c. molybdenum
d. magnesium
Q9.
A pink flowered Snapdragon plant was crossed with a red flowered Snapdragon plant. What type of
phenotype/s is/are expected in the progeny?
(1) Only pink flowered plants
(2) Red, Pink as well as white flowered plants
(3) Only red flowered plants
(4) Red flowered as well as pink flowered plants
Q10.
The process of appearance of recombination nodules occu

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 80,
          "preview": "Evaluate the correctness of two statements about cleistogamous flowers.",
          "fullText": "Given below are two statements: Statement I: Cleistogamous flowers are invariably autogamous. Statement II: Cleistogamy is disadvantageous as there is no chance for cross pollination. In the light of the above statements, choose the correct answer from the options given below. A. Statement I is incorrect but Statement II is correct B. Both Statement I and Statement II are correct C. Both Statement I and Statement II are incorrect D. Statement I is correct but Statement II is incorrect",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `numerical`


#### Example 1: `source_question_extraction-003`

- **Variation:** numerical
- **Tags:** cbse, source_upload, numerical, production_llm_gold

**Inputs**

**Document Text:**

Mathematics Board Testing Question Bank
4
Each question carries 5 marks. Comprehensive working, equations, diagrams and derivations may be
required.
Q37. If x = 3 sin t - sin 3t, y = 3 cos t - cos 3t, find dy/dx and prove that d²y/dx² = -(cosec³ 2t ·
cosec t)/3.
Q38. Prove that the line through points A(0, -1, -1) and B(4, 5, 1) intersects the line through
points C(3, 9, 4) and D(-4, 4, 4). Hence, write the equation of line passing through the point of
intersection of lines AB and CD as well as

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 37,
          "preview": "Find dy/dx and prove d²y/dx² = -(cosec³ 2t · cosec t)/3.",
          "fullText": "If x = 3 sin t - sin 3t, y = 3 cos t - cos 3t, find dy/dx and prove that d²y/dx² = -(cosec³ 2t · cosec t)/3.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 38,
          "preview": "Prove intersection of lines through points A and B with C and D.",
          "fullText": "Prove that the line through points A(0, -1, -1) and B(4, 5, 1) intersects the line through points C(3, 9, 4) and D(-4, 4, 4). Hence, write the equation of line passing through the point of intersection of lines AB and CD.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-005`

- **Variation:** numerical
- **Tags:** cbse, source_upload, numerical, production_llm_gold

**Inputs**

**Document Text:**

SECTION C — Short Answer Questions (SAQs)  
Each question carries 3 marks. Answer with the necessary details.  

Q27. Explain the mode of action of contraceptive pills taken by human females. Mention the schedule to be followed for effective outcome.  

Q28. (a) What are transgenic animals?  
(b) Name the first transgenic cow and state its importance.  
OR  
(a) Explain the convention for naming EcoRI.  
(b) With the help of an illustration only, show the action of EcoRI on a DNA polynucleotide.

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section C",
      "questions": [
        {
          "number": 27,
          "preview": "Explain the mode of action of contraceptive pills.",
          "fullText": "Explain the mode of action of contraceptive pills taken by human females. Mention the schedule to be followed for effective outcome.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 28,
          "preview": "What are transgenic animals? Name the first transgenic cow.",
          "fullText": "(a) What are transgenic animals? (b) Name the first transgenic cow and state its importance. OR (a) Explain the convention for naming EcoRI. (b) With the help of an illustration only, show the action of EcoRI on a DNA polynucleotide.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `source_question_extraction-018`

- **Variation:** numerical
- **Tags:** neet, source_upload, numerical, production_llm_gold

**Inputs**

**Document Text:**

Q1.
Read the following statements and choose the set
of correct statements.
In the members of Phaeophyceae.
A. Asexual reproduction occurs usually by
biflagellate zoospores.
B. Sexual reproduction is by oogamous method
only.
C. Stored food is in the form of carbohydrates
which is either mannitol or laminarin
D. The major pigments found are chlorophyll a,
c and carotenoids and xanthophyll.
E.
Vegetative cells have a cellulosic wall, usually covered on the outside by gelatinous coating of algin.
C

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 69,
          "preview": "Identify the CORRECT set of details from the following.",
          "fullText": "Identify the CORRECT set of details from the following: A. [Co(NH₃)₆]³⁺ : Inner orbital complex; d²sp³ hybridized B. [MnCl₆]³⁻ : Outer orbital complex; sp³d² hybridized C. [CoF₆]³⁻ : Outer orbital complex; d²sp³ hybridized D. [FeF₆]³⁻ : Outer orbital complex; sp³d² hybridized E. [Ni(CN)₄]²⁻ : Inner orbital complex; sp³ hybridized Choose the correct answer from the options given below: 1. A, B, C, D & E 2. C & D Only 3. A, B & D Only 4. A, C & E Only",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 70,
          "preview": "Given below",
          "fullText": "Given below",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `source_question_extraction-020`

- **Variation:** numerical
- **Tags:** neet, source_upload, numerical, production_llm_gold

**Inputs**

**Document Text:**

Q13.
The DNA present in chloroplast is:
(1) Linear, single stranded
(2) Circular, single stranded
(3) Linear, double stranded
(4) Circular, double stranded
Q14.
Which of the following are required for the dark reaction of photosynthesis?
A. Light
B. Chlorophyll
C. CO2
D. ATP
E. NADPH
Choose the correct answer from the options given
below:
(1) C, D and E only
(2) D and E only
(3) A, B and C only
(4) B, C and D only
Q15.
Identify the incorrect statement related to Pollination:
A. Moths and butterf

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 1,
          "preview": "Name conventional diagnosis methods and their disadvantages.",
          "fullText": "(b) “Early and accurate diagnosis of diseases is vital in medical technology.” (i) Name the conventional methods of diagnosis and their disadvantages.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 2,
          "preview": "Identify three diagnostic techniques from Biotechnology.",
          "fullText": "(ii) Which three diagnostic techniques have been developed through Biotechnology? Explain how each one helps in detecting diseases.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 3,
          "preview": "Explain the process of double fertilisation in flowering plants.",
          "fullText": "Q42. (a) (i) Explain how double fertilisation takes place in a flowering plant.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 4,
          "preview": "Discuss the fate of products of double fertilisation.",
          "fullText": "(ii) Write the fate of the products of double fertilization in these plants.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `assertion_reason`


#### Example 1: `source_question_extraction-006`

- **Variation:** assertion_reason
- **Tags:** cbse, source_upload, assertion_reason, production_llm_gold

**Inputs**

**Document Text:**

Q14.
Assertion (A): Ideal plane and convex mirror systems cannot produce real focus images under any practical
circumscribed experimental setup conditions.
Reason (R): A virtual image structure generated by a primary optics component can never serve as a valid
virtual object to produce a real image output from a secondary boundary element.
Q15.
Assertion (A): When a structural bar made of pure copper is placed inside an external magnetic field region,
the field flux lines get strongly concentrat

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 14,
          "preview": "Discuss the validity of ideal mirrors producing real focus images.",
          "fullText": "Assertion (A): Ideal plane and convex mirror systems cannot produce real focus images under any practical circumscribed experimental setup conditions. Reason (R): A virtual image structure generated by a primary optics component can never serve as a valid virtual object to produce a real image output from a secondary boundary element.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 15,
          "preview": "Explain the effect of magnetic fields on copper structural bars.",
          "fullText": "Assertion (A): When a structural bar made of pure copper is placed inside an external magnetic field region, the field flux lines get strongly concentrated.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `multi_section`


#### Example 1: `source_question_extraction-022`

- **Variation:** multi_section
- **Tags:** neet, source_upload, multi_section, production_llm_gold

**Inputs**

**Document Text:**

Q63.
Inhibition of Succinic dehydrogenase enzyme by malonate is a classical example of:
(1) Competitive inhibition
(2) Enzyme activation
(3) Cofactor inhibition
(4) Feedback inhibition
Q64.
Auxin is used by gardeners to prepare weed free lawns. But no damage is caused to grass as auxin;
(1) does not affect mature monocotyledonous
plants.
(2) can help in cell division in grasses, to produce
growth.
(3) promotes apical dominance.
(4) promotes abscission of mature leaves only.
Q65.
Identify the set

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 21,
          "preview": "Let satisfy for some. Then is equal to _______",
          "fullText": "Let satisfy for some. Then is equal to _______",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 22,
          "preview": "Let the centre of the circle be in the first quadrant and lie on the line.",
          "fullText": "Let the centre of the circle be in the first quadrant and lie on the line. Let the area of an equilateral triangle inscribed in the circle be. Then the square of the length of the chord of the circle on the line is _______.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 23,
          "preview": "If , and be three vectors such that and, then is equal to _______.",
          "fullText": "If , and be three vectors such that and, then is equal to _______.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 24,
          "preview": "For the functions , and , let. If the first term of a G.P. is ,",
          "fullText": "For the functions , and , let. If the first term of a G.P. is , its common ratio is and the sum of its first",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `footer_noise`


#### Example 1: `source_question_extraction-007`

- **Variation:** footer_noise
- **Tags:** cbse, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

Q22. The ground state energy of a hydrogen atom is given as -13.6 eV. Calculate the precise potential energy
value and kinetic energy value of the bound electron when the atom is excited to its third excited state
configuration.
Q23. A conducting wire of fixed total length L is bent sequentially into: (i) a square coil containing N total
turns, and (ii) a circular coil containing N total turns. The coil structure in both experimental cases is free to
pivot about a vertical axis coinciding with i
Footer scan artifact line — ignore — page 7

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 22,
          "preview": "Calculate potential and kinetic energy of a hydrogen atom's electron.",
          "fullText": "The ground state energy of a hydrogen atom is given as -13.6 eV. Calculate the precise potential energy value and kinetic energy value of the bound electron when the atom is excited to its third excited state configuration.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 23,
          "preview": "Analyze a conducting wire bent into square and circular coils.",
          "fullText": "A conducting wire of fixed total length L is bent sequentially into: (i) a square coil containing N total turns, and (ii) a circular coil containing N total turns. The coil structure in both experimental cases is free to pivot about a vertical axis coinciding with i.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-008`

- **Variation:** footer_noise
- **Tags:** cbse, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

Mathematics Board Testing Question Bank
1
MATHEMATICS TESTING QUESTION BANK
Class XII - Question Compendium
SECTION A: MULTIPLE CHOICE QUESTIONS (MCQS)
Each question carries 1 mark. Select the most appropriate option from the choices given below.
Q1. If |a| = 8, |b| = 3 and |a × b| = 12, then the value of |a · b| is:
(A) 6√3
(B) 8√3
(C) 12√3
(D) 3√12
Q2. If a square matrix A is such that A² = A and (I - A)³ = xA + I, then value of x must be:
(A) 7
(B) 5
(C) -7
(D) -1
Q3. The Cartesian equation o

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section E",
      "questions": [
        {
          "number": 47,
          "preview": "Describe the electric field in a parallel plate capacitor.",
          "fullText": "Q47. Passage: A parallel plate capacitor has two parallel plates which are separated by an insulating medium like air, mica, etc. When the plates are connected to the terminals of a battery, they get equal and opposite charges and an electric field is set up in between them. This electric field between the two plates depends upon the potential.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `source_question_extraction-014`

- **Variation:** footer_noise
- **Tags:** cbse, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

Q9. A galvanometer of resistance G is converted into an ammeter of range 0 to I A. If the current through the
galvanometer is 0.1% of I A, the total combined resistance of the ammeter circuit configuration is:
(A) G / 999 Ω
(B) G / 1000 Ω
(C) G / 1001 Ω
(D) G / 100.1 Ω
Q10. A charged particle gains a speed of 106 m/s when accelerated from rest through a potential difference of
10 kV. It enters a region of a uniform magnetic field of 0.4 T such that its velocity vector is perpendicular to the
mag
Footer scan artifact line — ignore — page 14

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section A",
      "questions": [
        {
          "number": 11,
          "preview": "Assertion about melanized moths and industrial areas.",
          "fullText": "Assertion (A): The population of melanized moths increased in industrial areas after Industrial Revolution. Reason (R): In industrial environments...",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `source_question_extraction-021`

- **Variation:** footer_noise
- **Tags:** neet, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

D. Bark refers to periderm and secondary phloem.
E. Phellogen is single-layered in thickness. Choose the
correct answer from the options given below:
a. B and C only
b. B. C and E only
c. A and D only
d. A, B and D only
Q43.
Given below are two Statements:
Statement I : Chromosomes become gradually visible
under light microscope during leptotene stage.
Statement II: The beginning of diplotene stage is
recognized by dissolution of synaptonemal complex.
In the light of the above statements, choose
Footer scan artifact line — ignore — page 21

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 9,
          "preview": "Find the total combined resistance of an ammeter circuit configuration.",
          "fullText": "A galvanometer of resistance G is converted into an ammeter of range 0 to I A. If the current through the galvanometer is 0.1% of I A, the total combined resistance of the ammeter circuit configuration is:",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 10,
          "preview": "Determine the behavior of a charged particle in a magnetic field.",
          "fullText": "A charged particle gains a speed of 10^6 m/s when accelerated from rest through a potential difference of 10 kV. It enters a region of a uniform magnetic field of 0.4 T such that its velocity vector is perpendicular to the mag",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 5: `source_question_extraction-023`

- **Variation:** footer_noise
- **Tags:** neet, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

d. bat pollinated plants
Q86.
Given below are two statements:
Statement I: Gause’s ‘Competitive Exclusive Principle’
states that two closely related species competing for the same related species competing for the same
resources cannot co-exist indefinitely and competitively inferior one will be eliminated eventually.
Statement II: In general, carnivores are more adversely
affected by competition than herbivores.
In the light of the above statements, choose the correct answer from the options gi

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 48,
          "preview": "Calculate the value of mass from energy released by proton bombardment.",
          "fullText": "The energy released when kg of is converted into by proton bombardment is eV. The value of is _______. (Nearest integer) (Mass of u, mass of u, mass of proton u and u MeV/c and Avogadro number)",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 49,
          "preview": "Determine the work done in moving a charge in an electric field.",
          "fullText": "A three coulomb charge moves from the point to the point in an electric field expressed as N/C. The work done in moving the charge is _______ J.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 50,
          "preview": "Find the pressure needed to compress a gas isothermally.",
          "fullText": "A certain gas is isothermally compressed to of its initial volume ( litre) by applying required pressure. If the bulk",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 6: `source_question_extraction-028`

- **Variation:** footer_noise
- **Tags:** cbse, source_upload, footer_noise, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 2
SECTION A — MCQs
Each question carries 1 mark. Select the most appropriate option.
Q1. Identify the plant in which emasculation is not required for artificial hybridization.
(A) Rice
(B) Wheat
(C) Pea
(D) Papaya
Q2. Which of the following is not a functional unit of an ecosystem?
(A) Energy flow
(B) Decomposition
(C) Stratification
(D) Productivity
Q3. Identify the statements that correctly describe Darwin’s Theory of Evolution.
(i) Overprodu
Footer scan artifact line — ignore — page 28

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 63,
          "preview": "Inhibition of Succinic dehydrogenase enzyme by malonate.",
          "fullText": "Inhibition of Succinic dehydrogenase enzyme by malonate is a classical example of: (1) Competitive inhibition (2) Enzyme activation (3) Cofactor inhibition (4) Feedback inhibition",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 64,
          "preview": "Auxin is used by gardeners to prepare weed free lawns.",
          "fullText": "Auxin is used by gardeners to prepare weed free lawns. But no damage is caused to grass as auxin; (1) does not affect mature monocotyledonous plants. (2) can help in cell division in grasses, to produce growth. (3) promotes apical dominance. (4) promotes abscission of mature leaves only.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 65,
          "preview": "Identify the set.",
          "fullText": "Identify the set",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `source_question_extraction-009`

- **Variation:** neet
- **Tags:** cbse, source_upload, neet, production_llm_gold

**Inputs**

**Document Text:**

Q30. An alternating voltage source represented by V = V0 sin ωt is applied across an ideal inductor possessing
self-inductance L. Derive the mathematical expression for the instantaneous current flowing through the circuit.
Prove analytically that the current wave lags behind the voltage wave by a phase angle of π / 2 radians, and
construct the corresponding vector phasor diagram layout.
Q31. Define the terms 'work function' and 'stopping potential' within the context of photoelectric emission
p

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 49,
          "preview": "Explain the photoelectric effect based on Planck's theory.",
          "fullText": "Passage: Einstein explained the photoelectric effect on the basis of Planck's quantum theory, where light travels in the form of small bundles of energy called photons. The energy of each photon is given by hν, where ν is the frequency of incident light and h is Planck's constant. The number of photons in a beam of light determines the intensity of the incident light. A photon incident on a metal surface transfers its total energy to a free electron in the metal. A part of this energy is u",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-024`

- **Variation:** neet
- **Tags:** cbse, source_upload, neet, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 10
SECTION E — Long Answer Questions (LAQs)
Each question carries 5 marks. Answer with detailed explanation wherever required.
Q37. Trace the events from fertilization till implantation of blastocyst in human female.
Also mention the site where fertilization takes place.
Q38. (a) (i) Watson and Crick’s discovery of double helical structure was based on
which two findings. Also mention the names of the scientists associated with these
findings.

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 1,
          "preview": "Choose the correct statements about Phaeophyceae.",
          "fullText": "Read the following statements and choose the set of correct statements. In the members of Phaeophyceae. A. Asexual reproduction occurs usually by biflagellate zoospores. B. Sexual reproduction is by oogamous method only. C. Stored food is in the form of carbohydrates which is either mannitol or laminarin D. The major pigments found are chlorophyll a, c and carotenoids and xanthophyll. E. Vegetative cells have a cellulosic wall, usually covered on the outside by gelatinous coating of algin.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `source_question_extraction-010`

- **Variation:** jee
- **Tags:** cbse, source_upload, jee, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 5
SECTION A — Assertion–Reasoning
Each question carries 1 mark. For each question choose the correct option: (A) Both A and R
are true and R is the correct explanation of A. (B) Both A and R are true but R is not the
correct explanation of A. (C) A is true but R is false. (D) A is false but R is true.
Q11. Assertion (A): The population of melanized moths increased in industrial areas
after Industrial Revolution.
Reason (R): In industrial enviro

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 51,
          "preview": "Explain how a galvanometer works and its components.",
          "fullText": "Passage: A galvanometer is an instrument used to show the direction and strength of the current passing through it. It essentially works on the fact that a current-carrying coil experiences a deflecting torque when placed in a magnetic field. A spring attached to the coil provides a counter torque. In equilibrium, the deflecting torque is balanced by the restoring torque of the spring: NBAI = kφ. A small resistance, called a shunt, of a suitable value is connected in parallel with the galvanometer.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-025`

- **Variation:** jee
- **Tags:** neet, source_upload, jee, production_llm_gold

**Inputs**

**Document Text:**

b. M phase
c. S phase
d. G1 phase
Q34.
How many molecules of ATP and NADPH are required for every molecule of CO2 fixed in the Calvin cycle?
(1) 3 molecules of ATP and 3 molecules of
NADPH
(2) 3 molecules of ATP and 2 molecules of
NADPH
(3) 2 molecules of ATP and 3 molecules of
NADPH
(4) 2 molecules of ATP and 2 molecules of
NADPH
Q35.
What is the function of tassels in the corn cob?
a. To protect seeds
b. To attract insects
c. To trap pollen grains
d. To disperse pollen grains
Q36.
The lactose

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 8,
          "preview": "Which micronutrient is needed for water splitting in photosynthesis?",
          "fullText": "Which micronutrient is required for splitting of water molecule during photosynthesis? a. copper b. manganese c. molybdenum d. magnesium",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 9,
          "preview": "What phenotypes are expected from crossing pink and red Snapdragon plants?",
          "fullText": "A pink flowered Snapdragon plant was crossed with a red flowered Snapdragon plant. What type of phenotype/s is/are expected in the progeny? (1) Only pink flowered plants (2) Red, Pink as well as white flowered plants (3) Only red flowered plants (4) Red flowered as well as pink flowered plants",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 10,
          "preview": "Describe the process of appearance of recombination nodules.",
          "fullText": "The process of appearance of recombination nodules occurs...",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `source_question_extraction-011`

- **Variation:** cbse
- **Tags:** cbse, source_upload, cbse, production_llm_gold

**Inputs**

**Document Text:**

SECTION D: LONG ANSWER QUESTIONS (LAQS)
Each question carries 5 marks. Comprehensive solutions detailing equations, schematic diagrams, and thorough
derivations are required.
Q37. (a)  Generalize  the  mathematical  relation  for  refraction  across  a  single  curved  spherical  interface
separating two media of distinct refractive indices. Utilizing this, derive the step-by-step expression for the
Lens Maker's Formula for a thin biconvex lens element.
(b) Define the optical power parameters of

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section A",
      "questions": [
        {
          "number": 1,
          "preview": "If |a| = 8, |b| = 3 and |a × b| = 12, then find |a · b|.",
          "fullText": "If |a| = 8, |b| = 3 and |a × b| = 12, then the value of |a · b| is: (A) 6√3 (B) 8√3 (C) 12√3 (D) 3√12",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 2,
          "preview": "Find the value of x if A² = A and (I - A)³ = xA + I.",
          "fullText": "If a square matrix A is such that A² = A and (I - A)³ = xA + I, then value of x must be: (A) 7 (B) 5 (C) -7 (D) -1",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 3,
          "preview": "The Cartesian equation of a line is given.",
          "fullText": "The Cartesian equation of a line is given.",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-026`

- **Variation:** cbse
- **Tags:** neet, source_upload, cbse, production_llm_gold

**Inputs**

**Document Text:**

B. Co-extinction
C. Mutation
D. Habitat loss and fragmentation
E.
Migration
Choose the correct option:
(1) A, B and E only
(2) A, B and D only
(3) A, C and D only
(4) A, B, C and D only
Q68.
Which of the following combinations is required for chemiosmosis?
a. proton pump, electron gradient, NADP synthase
b. membrane, proton pump, proton gradient. ATP synthase
c. membrane, proton pump, proton gradient, NADP synthase
d. proton pump, electron gradient, ATP synthase
Q69.
A transcription unit in DNA

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 13,
          "preview": "The DNA present in chloroplast is: (1) Linear, single stranded...",
          "fullText": "The DNA present in chloroplast is: (1) Linear, single stranded (2) Circular, single stranded (3) Linear, double stranded (4) Circular, double stranded",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 14,
          "preview": "Which of the following are required for the dark reaction of photosynthesis?",
          "fullText": "Which of the following are required for the dark reaction of photosynthesis? A. Light B. Chlorophyll C. CO2 D. ATP E. NADPH Choose the correct answer from the options given below: (1) C, D and E only (2) D and E only (3) A, B and C only (4) B, C and D only",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 15,
          "preview": "Identify the incorrect statement related to Pollination:",
          "fullText": "Identify the incorrect statement related to Pollination: A. Moths and butterf",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `diagram_ref`


#### Example 1: `source_question_extraction-012`

- **Variation:** diagram_ref
- **Tags:** neet, source_upload, diagram_ref, production_llm_gold

**Inputs**

**Document Text:**

Q80.
Given below are two statements:
Statement I: Cleistogamous flowers are invariably autogamous.
Statement II: Cleistogamy is disadvantageous as there is no chance for cross pollination.
In the light of the above statements, choose the correct answer from the options given below.
A. Statement I is incorrect but Statement II is correct
B. Both Statement I and Statement II are correct
C. Both Statement I and Statement II are incorrect
D. Statement I is correct but Statement II is incorrect
Q81.

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 30,
          "preview": "Derive expression for current in an inductor with AC voltage.",
          "fullText": "An alternating voltage source represented by V = V0 sin ωt is applied across an ideal inductor possessing self-inductance L. Derive the mathematical expression for the instantaneous current flowing through the circuit. Prove analytically that the current wave lags behind the voltage wave by a phase angle of π / 2 radians, and construct the corresponding vector phasor diagram layout.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 31,
          "preview": "Define 'work function' and 'stopping potential' in photoelectric emission.",
          "fullText": "Define the terms 'work function' and 'stopping potential' within the context of photoelectric emission.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-027`

- **Variation:** diagram_ref
- **Tags:** neet, source_upload, diagram_ref, production_llm_gold

**Inputs**

**Document Text:**

NEET Zoology Golden Set v1.0 | Page 9
Who proposed that the genetic code for amino acids
should be made up of three nucleotides?
(1) George Gamow
(2) Francis Crick
(3) Jacque Monod
(4) Franklin Stahl
Q21.
Which of the following type of immunity is present
at the time of birth and is a non-specific type of
defence in the human body?
(1) Acquired Immunity
(2) Innate Immunity
(3) Cell-mediated Immunity
(4) Humoral Immunity
Q22.
The unique mammalian characteristics are:
a. pinna, monocondylic skull

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 1,
          "preview": "Choose the correct answer from the options given below.",
          "fullText": "Choose the correct answer from the options given below: a. B and C only b. B, C and E only c. A and D only d. A, B and D only",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 2,
          "preview": "Given below are two Statements regarding chromosomes.",
          "fullText": "Given below are two Statements: Statement I: Chromosomes become gradually visible under light microscope during leptotene stage. Statement II: The beginning of diplotene stage is recognized by dissolution of synaptonemal complex. In the light of the above statements, choose.",
          "pageHint": null,
          "confidence": "low"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `source_question_extraction-013`

- **Variation:** case_study
- **Tags:** cbse, source_upload, case_study, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 11
OR
(b) “Early and accurate diagnosis of diseases is vital in medical technology.”
(i) Name the conventional methods of diagnosis and their disadvantages.
(ii) Which three diagnostic techniques have been developed through Biotechnology?
Explain how each one helps in detecting diseases.
Q42. (a) (i) Explain how double fertilisation takes place in a flowering plant.
(ii) Write the fate of the products of double fertilization in these plants.
OR

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 5,
          "preview": "Find the sum of all real solutions of a logarithmic equation.",
          "fullText": "The sum of all the real solutions of the equation log(x+3)(6x² + 28x + 30) = 5 - 2 log(6x + 10)(x² + 6x + 9) is equal to",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 6,
          "preview": "Determine the least value of a trigonometric expression.",
          "fullText": "The least value of (cos² θ - 6 sin θ cos θ + 3 sin² θ + 2) is",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 7,
          "preview": "Analyze a relation defined on set A with two statements.",
          "fullText": "Let A = {0, 1, 2, ..., 9}. Let R be a relation on A defined by (x, y) ∈ R if and only if |x - y| is a multiple of 3. Given below are two statements: Statement I: n(R) = 36. Statement II: R is an equivalence relation.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `source_question_extraction-029`

- **Variation:** multi_part
- **Tags:** cbse, source_upload, multi_part, production_llm_gold

**Inputs**

**Document Text:**

CBSE Class XII Biology — Testing Question Bank
Page 3
Q5. You know that there are twenty different types of naturally occurring amino acids
and four different types of bases in the DNA. A combination of 3 such bases codes for a
specific amino acid. If instead there are 96 different amino acids and 12 different
bases in the DNA, then the minimum number of combination of bases required to form
a codon is:
(A) 6
(B) 8
(C) 2
(D) 4
Q6. The rate of formation of new organic matter by consumers, and the

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": null,
      "questions": [
        {
          "number": 86,
          "preview": "Evaluate two statements about species competition.",
          "fullText": "Given below are two statements: Statement I: Gause’s ‘Competitive Exclusive Principle’ states that two closely related species competing for the same related species competing for the same resources cannot co-exist indefinitely and competitively inferior one will be eliminated eventually. Statement II: In general, carnivores are more adversely affected by competition than herbivores. In the light of the above statements, choose the correct answer from the options given.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

## Variation: `low_confidence`


#### Example 1: `source_question_extraction-015`

- **Variation:** low_confidence
- **Tags:** jee, source_upload, low_confidence, production_llm_gold

**Inputs**

**Document Text:**

Q21.
Let 
 satisfy 
 for some
. Then 
 is equal to _______
Q22.
Let the centre of the circle 
 be in the first quadrant and lie on the line 
.
Let the area of an equilateral triangle inscribed in the circle be 
. Then the square of the length of the chord of
the circle on the line 
 is _______.
Q23.
If 
, 
 and  be three vectors such that 
 and 
, then 
 is equal to
_______.
Q24.
For the functions 
, and 
, 
, let
. If the first term of a G.P. is 
, its common ratio is 
 and the sum of
its first

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section D",
      "questions": [
        {
          "number": 37,
          "preview": "Generalize the mathematical relation for refraction across a curved interface.",
          "fullText": "(a) Generalize the mathematical relation for refraction across a single curved spherical interface separating two media of distinct refractive indices. Utilizing this, derive the step-by-step expression for the Lens Maker's Formula for a thin biconvex lens element.\n(b) Define the optical power parameters of",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `source_question_extraction-030`

- **Variation:** low_confidence
- **Tags:** cbse, source_upload, low_confidence, production_llm_gold

**Inputs**

**Document Text:**

PHYSICS TESTING QUESTION BANK
Class XII — Question Compendium
SECTION A: MULTIPLE CHOICE QUESTIONS (MCQS)
Each question carries 1 mark. Select the most appropriate option from the choices given below.
Q1. In a region, the electric field is given by E = 4xî N/C. The potential difference between points A (x = 1 m)
and B (x = 3 m), (VA - VB), is:
(A) -16 V
(B) 16 V
(C) -8 V
(D) 8 V
Q2. In an unbiased p-n junction, at equilibrium, which of the following statements is true?
(A) Diffusion current is z

**Expected output**

**Sections Json:**

```json
{
  "sections": [
    {
      "label": "Section E",
      "questions": [
        {
          "number": 37,
          "preview": "Trace events from fertilization to implantation in humans.",
          "fullText": "Trace the events from fertilization till implantation of blastocyst in human female. Also mention the site where fertilization takes place.",
          "pageHint": null,
          "confidence": "high"
        },
        {
          "number": 38,
          "preview": "Discuss Watson and Crick’s findings on DNA structure.",
          "fullText": "(a) (i) Watson and Crick’s discovery of double helical structure was based on which two findings. Also mention the names of the scientists associated with these findings.",
          "pageHint": null,
          "confidence": "high"
        }
      ]
    }
  ]
}
```

**Quality Check:** question_count: pass. full_text_complete: pass. no_hallucination: pass. confidence_calibration: pass. production_llm_gold: pass.

---

