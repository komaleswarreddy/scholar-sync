## 12. Studio Flashcards Generator

| Field | Value |
|-------|-------|
| Dataset ID | `studio_flashcards` |
| Category | Studio |
| Tier | Tier 2 |
| Target examples | 22 |
| Actual examples | 22 |
| Version | 1.1.0 |

**Agent responsibility:** JSON array of `{front, back}` flashcards from retrieved excerpts. Card count varies by excerpt density (default 5–10; custom instructions override). Multi-source → one integrated deck spread across sources.

**Audit finding (baseline v1.0.0):** The original dataset used a fixed deck size regardless of excerpt density and lacked true multi-source card spread. Rebuilt with variable card counts, locked scope variation taxonomy, full inline system + task prompts, and gold decks that honor custom count overrides.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `per_concept` | Topic-focused custom instructions | 4 |
| `multi_concept` | Full-breadth / all topics in context | 3 |
| `per_source` | Single-source excerpt | 4 |
| `multi_source` | Merged multi-doc context + synthesis | 5 |
| `no_source` | Empty context → `[]` — no fabrication | 2 |
| `custom_override` | Count/difficulty overrides | 4 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **card_count_variable** — Deck size matches excerpt density and custom_instructions.
* **no_duplicates** — No same-idea cards reworded; distinct front/back pairs.
* **multi_source_spread** — Multi-source decks draw cards from each represented source.
* **grounding** — Card backs grounded in context excerpt only.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `context`, `selected_source_count`
* Output keys: `flashcards_json`
* Production also uses: `custom_instructions`, `retrieval_queries_note`

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
You are an **expert instructional designer**. Build a **digital flashcard deck** for spaced review.

**Selected sources:** {{ selected_source_count }} document(s).

## Source scope (mandatory)
- Use **only** the Source content excerpt below.
- Do not use outside knowledge or material not in the excerpt.

{% if selected_source_count | int > 1 %}
## Deck strategy (multi-source)
- Build **one integrated deck** — not separate piles per file.
- Spread cards so **each represented source** contributes when the excerpt includes it.
- Mix card order freely; avoid long runs from a single subsection unless the excerpt justifies it.
{% else %}
## Deck strategy (single-source)
- Prioritize **core definitions**, **key facts**, and **central concepts** from that document.
{% endif %}

## Card shape
- **`front`:** short question, term, or prompt (one line when possible).
- **`back`:** answer or definition, grounded in the excerpt.
- No duplicate ideas; prioritize the most study-worthy items when the excerpt is dense.

## Output
- Return **only** a JSON array of objects: `{"front":"…","back":"…"}`.
- Target **8–15** cards when the excerpt supports it; fewer if thin; never pad with invented facts.

{% if retrieval_queries_note and retrieval_queries_note.strip() %}
Retrieval queries (alignment only — do not copy as card text):
{{ retrieval_queries_note }}

{% endif %}
{% if context and context.strip() %}
### Source content
{{ context }}
{% else %}
No source content provided. Return exactly:
[{"front":"Insufficient source text","back":"No indexed excerpt was retrieved for the selected sources. Re-index or reselect sources and try again."}]
{% endif %}

{% if custom_instructions %}
### Additional user instructions
{{ custom_instructions }}
{% endif %}
```

*Runtime note:* [`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) `StudioService._generate_structured_task()` with flashcards task template.

**Scope coverage**

| scope_mode | Min examples | This dataset |
|------------|--------------|--------------|
| per_concept | 4 | 4 |
| multi_concept | 3 | 3 |
| per_source | 4 | 4 |
| multi_source | 5 | 5 |
| no_source | 2 | 2 |
| custom_override | — | 4 (distributed) |

### Evaluation examples (22)
## Variation: `per_concept`


#### Example 1: `studio_flashcards-001`

- **Variation:** per_concept
- **Tags:** cbse, physics, scope_mode:per_concept, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Selected Source Count:**

1

**Custom Instructions:**

8 cards max, focus Ohm's law only

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Ohm's law?",
    "back": "V = IR for ohmic conductors."
  },
  {
    "front": "Series R_eq?",
    "back": "R_eq = R1 + R2"
  },
  {
    "front": "Parallel rule?",
    "back": "1/R_eq = 1/R1 + 1/R2"
  },
  {
    "front": "Kirchhoff junction?",
    "back": "Sum I_in = sum I_out"
  },
  {
    "front": "Drift velocity relation?",
    "back": "I = neAv_d"
  },
  {
    "front": "Resistivity formula?",
    "back": "ρ = RA/l"
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 2: `studio_flashcards-002`

- **Variation:** per_concept
- **Tags:** neet, biology, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Selected Source Count:**

1

**Custom Instructions:**

5 cards, digestive enzymes only

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Salivary amylase site?",
    "back": "Mouth — starts starch digestion."
  },
  {
    "front": "Pepsin medium?",
    "back": "Acidic stomach with HCl."
  },
  {
    "front": "Trypsin source?",
    "back": "Pancreatic juice → duodenum."
  },
  {
    "front": "Lipase function?",
    "back": "Digests fats."
  },
  {
    "front": "Main absorption?",
    "back": "Small intestine villi"
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 3: `studio_flashcards-003`

- **Variation:** per_concept
- **Tags:** cbse, chemistry, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Coordination number?",
    "back": "Count of σ-donor atoms on metal."
  },
  {
    "front": "Ligand?",
    "back": "Ion/molecule bonded to central metal."
  },
  {
    "front": "[Fe(CN)6]4- CN?",
    "back": "6"
  },
  {
    "front": "IUPAC ligand order?",
    "back": "Alphabetical; anionic ligands end in -o"
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 4: `studio_flashcards-004`

- **Variation:** per_concept
- **Tags:** cbse, mathematics, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Classical P(E)?",
    "back": "Favourable / total outcomes."
  },
  {
    "front": "Addition rule?",
    "back": "P(A∪B)=P(A)+P(B)-P(A∩B)"
  },
  {
    "front": "Independent events?",
    "back": "P(A∩B)=P(A)P(B)"
  },
  {
    "front": "Bayes links?",
    "back": "Prior, likelihood → posterior"
  },
  {
    "front": "Complement?",
    "back": "P(A')=1-P(A)"
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

## Variation: `multi_concept`


#### Example 1: `studio_flashcards-005`

- **Variation:** multi_concept
- **Tags:** cbse, biology, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2. Mitosis: growth/repair, same chromosome number. Meiosis: gametes, halves chromosomes. Prophase I: crossing over.

**Selected Source Count:**

1

**Custom Instructions:**

Full breadth, 8 cards

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Light reaction site?",
    "back": "Grana — ATP, NADPH."
  },
  {
    "front": "Calvin cycle?",
    "back": "Stroma — CO2 fixation."
  },
  {
    "front": "Mitosis purpose?",
    "back": "Growth/repair, same 2n."
  },
  {
    "front": "Meiosis output?",
    "back": "Gametes with n chromosomes."
  },
  {
    "front": "Crossing over?",
    "back": "Prophase I of meiosis."
  },
  {
    "front": "Stomata role?",
    "back": "Gas exchange CO2/O2."
  },
  {
    "front": "Chlorophyll?",
    "back": "Absorbs light energy."
  },
  {
    "front": "ATP use in Calvin?",
    "back": "Powers CO2 fixation."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 2: `studio_flashcards-006`

- **Variation:** multi_concept
- **Tags:** cbse, chemistry, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Kc=[products]/[reactants] at equilibrium. Le Chatelier: stress shifts to oppose change. Catalyst speeds approach, not K. Alkanes CnH2n+2. Markovnikov: H to C with more H. Benzene: delocalized π, extra stability.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Kc definition?",
    "back": "Equilibrium concentration ratio."
  },
  {
    "front": "Le Chatelier?",
    "back": "Shift opposes applied stress."
  },
  {
    "front": "Catalyst and K?",
    "back": "No change to K."
  },
  {
    "front": "Alkane formula?",
    "back": "CnH2n+2"
  },
  {
    "front": "Markovnikov rule?",
    "back": "H to C with more H."
  },
  {
    "front": "Benzene stability?",
    "back": "Delocalized π electrons."
  },
  {
    "front": "Pressure on fewer moles?",
    "back": "Shifts toward fewer gas moles."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 3: `studio_flashcards-007`

- **Variation:** multi_concept
- **Tags:** cbse, mathematics, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd. Graph ax+by≤c: shade toward origin test point. Feasible region intersection of half-planes. Optimize at vertices.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Binomial general term?",
    "back": "Tr+1 = nCr a^(n-r) b^r"
  },
  {
    "front": "nCr meaning?",
    "back": "Combination coefficient."
  },
  {
    "front": "Feasible region?",
    "back": "Intersection of constraint half-planes."
  },
  {
    "front": "Corner point method?",
    "back": "Optimize at polygon vertices."
  },
  {
    "front": "Shade ax+by≤c?",
    "back": "Test origin side."
  },
  {
    "front": "Middle term n even?",
    "back": "Single middle at r=n/2."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

## Variation: `per_source`


#### Example 1: `studio_flashcards-008`

- **Variation:** per_source
- **Tags:** cbse, physics, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Lens formula?",
    "back": "1/f = 1/v − 1/u"
  },
  {
    "front": "Magnification?",
    "back": "m = v/u"
  },
  {
    "front": "Lens power?",
    "back": "P = 1/f (f in m)"
  },
  {
    "front": "Real object u?",
    "back": "Negative in Cartesian convention."
  },
  {
    "front": "Optical centre ray?",
    "back": "Passes undeviated."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 2: `studio_flashcards-009`

- **Variation:** per_source
- **Tags:** cbse, biology, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "A pairs with?",
    "back": "T"
  },
  {
    "front": "G pairs with?",
    "back": "C"
  },
  {
    "front": "Replication type?",
    "back": "Semiconservative."
  },
  {
    "front": "mRNA role?",
    "back": "Carries code to ribosomes."
  },
  {
    "front": "Translation site?",
    "back": "Ribosomes."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 3: `studio_flashcards-010`

- **Variation:** per_source
- **Tags:** cbse, chemistry, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Galvanic anode?",
    "back": "Oxidation."
  },
  {
    "front": "Galvanic cathode?",
    "back": "Reduction."
  },
  {
    "front": "E°cell?",
    "back": "E°cathode − E°anode."
  },
  {
    "front": "Nernst equation?",
    "back": "Links EMF to concentration."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 4: `studio_flashcards-011`

- **Variation:** per_source
- **Tags:** cbse, mathematics, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.

**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Direction cosines constraint?",
    "back": "l²+m²+n²=1"
  },
  {
    "front": "3D line form?",
    "back": "(x-x1)/a=(y-y1)/b=(z-z1)/c"
  },
  {
    "front": "Skew line distance?",
    "back": "Uses cross product."
  },
  {
    "front": "Direction ratios?",
    "back": "Define line direction."
  },
  {
    "front": "Angles with?",
    "back": "Coordinate axes."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

## Variation: `multi_source`


#### Example 1: `studio_flashcards-012`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

[Source A — Current Electricity] Ohm's law V=IR; resistivity ρ=RA/l.

[Source B — Electrochemistry] Galvanic cell: anode oxidation; E°cell=E°cathode-E°anode.

**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Ohm's law?",
    "back": "V=IR"
  },
  {
    "front": "ρ relation?",
    "back": "ρ=RA/l"
  },
  {
    "front": "Galvanic anode?",
    "back": "Oxidation."
  },
  {
    "front": "E°cell?",
    "back": "E°cathode−E°anode"
  },
  {
    "front": "Series R?",
    "back": "Adds."
  },
  {
    "front": "Charge flow link?",
    "back": "Both domains involve charge/energy."
  },
  {
    "front": "Resistivity vs cell?",
    "back": "Material vs electrochemical driving force."
  },
  {
    "front": "Integrated review?",
    "back": "Electricity + electrochemistry deck."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 2: `studio_flashcards-013`

- **Variation:** multi_source
- **Tags:** cbse, biology, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

[Source A — Photosynthesis] Light reaction in grana; Calvin cycle in stroma.

[Source B — Cell division] Mitosis maintains chromosome number; meiosis halves for gametes.

**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Grana product?",
    "back": "ATP, NADPH"
  },
  {
    "front": "Calvin site?",
    "back": "Stroma"
  },
  {
    "front": "Meiosis result?",
    "back": "n gametes"
  },
  {
    "front": "Mitosis?",
    "back": "2n somatic cells."
  },
  {
    "front": "Crossing over?",
    "back": "Prophase I."
  },
  {
    "front": "Gas exchange?",
    "back": "Stomata."
  },
  {
    "front": "Integrated theme?",
    "back": "Energy and information in cells."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 3: `studio_flashcards-014`

- **Variation:** multi_source
- **Tags:** cbse, mathematics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

[Source A — Probability] P(E)=favourable/total; P(A∩B)=P(A)P(B) if independent.

[Source B — Binomial] Tr+1=nCr a^(n-r) b^r in (a+b)^n expansion.

**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[
  {
    "front": "P(E) classical?",
    "back": "favourable/total"
  },
  {
    "front": "Independent?",
    "back": "P(A∩B)=P(A)P(B)"
  },
  {
    "front": "Binomial term?",
    "back": "nCr a^(n-r) b^r"
  },
  {
    "front": "nCr?",
    "back": "Combination count."
  },
  {
    "front": "Link?",
    "back": "Combinatorics in probability."
  },
  {
    "front": "Deck spans?",
    "back": "Both sources."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 4: `studio_flashcards-015`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Lens formula?",
    "back": "1/f=1/v−1/u"
  },
  {
    "front": "P=?",
    "back": "1/f"
  },
  {
    "front": "V=IR?",
    "back": "Ohm's law"
  },
  {
    "front": "Series R?",
    "back": "R1+R2"
  },
  {
    "front": "m=?",
    "back": "v/u"
  },
  {
    "front": "Real u sign?",
    "back": "Negative"
  },
  {
    "front": "Kirchhoff junction?",
    "back": "ΣI_in=ΣI_out"
  },
  {
    "front": "Optics+electricity?",
    "back": "Two-source deck."
  },
  {
    "front": "Review tip?",
    "back": "Separate formula cards per topic."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 5: `studio_flashcards-016`

- **Variation:** multi_source
- **Tags:** neet, biology, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.

**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Amylase?",
    "back": "Mouth"
  },
  {
    "front": "Pepsin?",
    "back": "Stomach HCl"
  },
  {
    "front": "Calvin?",
    "back": "Stroma CO2 fix"
  },
  {
    "front": "Grana?",
    "back": "Light reaction"
  },
  {
    "front": "Trypsin?",
    "back": "Pancreatic/duodenum"
  },
  {
    "front": "Absorption?",
    "back": "Small intestine"
  },
  {
    "front": "ATP use?",
    "back": "Calvin cycle"
  },
  {
    "front": "NEET deck?",
    "back": "Cross-topic."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

## Variation: `no_source`


#### Example 1: `studio_flashcards-017`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source
- **selected_source_count:** 1

**Inputs**

**Context:**



**Selected Source Count:**

1

**Expected output**

**Flashcards Json:**

[]

**Quality Check:** empty_deck: pass. no_fabrication: pass.

---

#### Example 2: `studio_flashcards-018`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source
- **selected_source_count:** 2

**Inputs**

**Context:**



**Selected Source Count:**

2

**Expected output**

**Flashcards Json:**

[]

**Quality Check:** empty_deck: pass. no_fabrication: pass.

---

## Variation: `custom_override`


#### Example 1: `studio_flashcards-019`

- **Variation:** custom_override
- **Tags:** cbse, physics, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Superconductivity at low T mentioned briefly.

**Selected Source Count:**

1

**Custom Instructions:**

Exactly 2 cards from thin excerpt

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Superconductivity note?",
    "back": "Zero resistance at very low temperature (thin excerpt)."
  },
  {
    "front": "Deck size?",
    "back": "Minimal 2-card deck from thin text."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 2: `studio_flashcards-020`

- **Variation:** custom_override
- **Tags:** cbse, biology, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Dicot root: radial vascular bundle. Monocot: polyarch xylem. Casparian strip in endodermis controls flow. Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Selected Source Count:**

1

**Custom Instructions:**

10 flashcards

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Dicot root vascular?",
    "back": "Radial bundle."
  },
  {
    "front": "Monocot xylem?",
    "back": "Polyarch."
  },
  {
    "front": "Casparian strip?",
    "back": "Suberin in endodermis."
  },
  {
    "front": "Apoplastic block?",
    "back": "Forces symplastic path."
  },
  {
    "front": "Salivary amylase?",
    "back": "Mouth."
  },
  {
    "front": "Pepsin?",
    "back": "Stomach."
  },
  {
    "front": "Villi?",
    "back": "Absorption."
  },
  {
    "front": "Endodermis role?",
    "back": "Selective uptake."
  },
  {
    "front": "Plant-animal link?",
    "back": "Surface area for absorption."
  },
  {
    "front": "10-card deck?",
    "back": "Dense excerpt supports more cards."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 3: `studio_flashcards-021`

- **Variation:** custom_override
- **Tags:** cbse, chemistry, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Tollens' test: silver mirror with aldehydes, not ketones. C=O undergoes nucleophilic addition.

**Selected Source Count:**

1

**Custom Instructions:**

Exactly 3 flashcards

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Tollens'?",
    "back": "Silver mirror — aldehydes."
  },
  {
    "front": "Ketones Tollens'?",
    "back": "No reaction."
  },
  {
    "front": "C=O mechanism?",
    "back": "Nucleophilic addition."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---

#### Example 4: `studio_flashcards-022`

- **Variation:** custom_override
- **Tags:** cbse, mathematics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 3

**Inputs**

**Context:**

Parabola: focus-directrix equidistance. y²=4ax focus (a,0). e=1 for parabola.

P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd.

**Selected Source Count:**

3

**Expected output**

**Flashcards Json:**

[
  {
    "front": "Parabola e?",
    "back": "1"
  },
  {
    "front": "Focus-directrix?",
    "back": "Equidistant locus."
  },
  {
    "front": "y²=4ax focus?",
    "back": "(a,0)"
  },
  {
    "front": "P(A∪B)?",
    "back": "P(A)+P(B)-P(A∩B)"
  },
  {
    "front": "Tr+1?",
    "back": "nCr a^(n-r) b^r"
  },
  {
    "front": "Three-source deck?",
    "back": "Spread across math topics."
  },
  {
    "front": "Review order?",
    "back": "Mix conic + probability + binomial."
  }
]

**Quality Check:** card_count: pass. no_duplicates: pass. grounding: pass.

---
