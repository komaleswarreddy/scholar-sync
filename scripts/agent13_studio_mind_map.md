## 13. Studio Mind Map Generator

| Field | Value |
|-------|-------|
| Dataset ID | `studio_mind_map` |
| Category | Studio |
| Tier | Tier 2 |
| Target examples | 24 |
| Actual examples | 24 |
| Version | 1.1.0 |

**Agent responsibility:** Hub-and-spoke Markdown mind map from source excerpts. Production **forces `sources_only`** context mode. Multi-source → one integrated hub bridging materials ([`mind_map_prompt.j2`](packages/core/prompts/templates/studio/mind_map_prompt.j2)).

**Audit finding (baseline v1.0.0):** The original dataset had all selected_source_count=1, weak hub-and-spoke gold, and no multi-source synthesis examples. Rebuilt with 8+ multi-source cases, locked variation taxonomy, full inline prompts, and gold maps with single `#` hub and integrated branches.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `per_concept` | Topic-focused custom instructions | 4 |
| `multi_concept` | Full-breadth / all topics in context | 3 |
| `per_source` | Single-source excerpt | 4 |
| `multi_source` | Merged multi-doc context + synthesis | 8 |
| `no_source` | Empty context → `# Insufficient source text` | 2 |
| `custom_override` | User focus/restrict overrides | 3 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **single_hub** — Exactly one `#` central hub; branches under `##`/`###`.
* **multi_source_synthesis** — Multi-source maps bridge materials, not siloed mini-maps.
* **structure** — Hub-and-spoke Markdown hierarchy; scannable headings.
* **grounding** — Nodes grounded in context excerpt only.
* **insufficient_source_pattern** — Empty context yields `# Insufficient source text` pattern.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `context`, `selected_source_count`
* Output keys: `mind_map_markdown`

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
You are an **expert in visual knowledge mapping** and **instructional design**. Produce a **mind map as Markdown**: **one central hub** with **branches** that show how ideas **connect to the whole**.

**Selected source count for this request:** **{{ selected_source_count }}** document(s). Retrieval pulled chunks **only** from these selected IDs (no other uploads).

---

## Non-negotiable scope (evidence only)

1. **Use ONLY the “Source content” excerpt below.**  
2. **Do not** import facts from outside that excerpt (no other notebooks, no generic textbook filler).  
3. If something is **not** in the excerpt, **omit** it—do not invent.  
{% if selected_source_count | int > 1 %}
4. **Multi-source synthesis (required):** The excerpt may combine passages from **{{ selected_source_count }}** different documents. You must **analyze them together**, not as if only one document existed.  
   - Choose **one** central `#` theme that **bridges** the materials when possible—an **overarching idea**, **shared pattern**, or **meaningful contrast** that still **grounds every branch in the excerpt** (e.g. two domains might meet under a hub like “Human response and regulation” if both biological control and interpersonal behavior appear in the text).  
   - Use **`##` major branches** to organize **by theme or by source-domain**, but **always** tie them back to the hub so the map feels **integrated**, not two disconnected mini-maps.  
   - **Explicitly surface** where useful: **overlapping concepts**, **parallel structures**, or **contrasts** between the texts—**only** if the excerpt supports them.  
   - **Forbidden:** Building the entire map from **one** source’s content while **ignoring** the other(s) when the excerpt clearly contains both. Spread attention across **all** represented sources unless one source dominates the excerpt length—in that case still name the secondary source’s ideas in at least one substantial `##` or `###` branch when they appear.  
{% else %}
4. **Single source:** The hub and branches should reflect **that one** document’s central theme, arguments, and structure.  
{% endif %}

{% if retrieval_queries_note and retrieval_queries_note.strip() %}
### Retrieval intent (alignment only — not labels to copy)
{{ retrieval_queries_note }}

{% endif %}
{% if context and context.strip() %}
### Source content (selected sources only)
{{ context }}
{% else %}
### Source content
No excerpt retrieved. Output a minimal map: `# Insufficient source text` plus `##` branches noting missing indexing/selection—**no** fabricated topic.
{% endif %}

---

## Structure (Markdown)

- **Exactly one** `# …` = **central hub** (short, specific—**synthetic** when multiple sources, not “Source A and B”).  
- **`## …`** = major branches (themes, domains, or comparison arms) **linked to the hub**.  
- **`### …`** and **`-`** = sub-concepts, mechanisms, examples **from the excerpt**.  
- Headings **2–8 words** where possible; bullets scannable.

Plan **internally**; output **only** the Markdown tree.

---

## Anti-patterns

- More than one `#` hub.  
- **Multi-source:** two unrelated silos with no hub relationship.  
- **Multi-source:** map dominated by one document when the excerpt clearly includes **both**.  
- Vague nodes (“Key ideas”) without **concrete** wording from the text.  
- External knowledge not in the excerpt.

{% if custom_instructions %}
### Additional user instructions
{{ custom_instructions }}
{% endif %}

**Output:** Markdown only — no code fences, no preamble.
```

*Runtime note:* [`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) with **`sources_only`** override; multi-source uses `merge_studio_match_lists` for integrated retrieval.

**Scope coverage**

| scope_mode | Min examples | This dataset |
|------------|--------------|--------------|
| per_concept | 4 | 4 |
| multi_concept | 3 | 3 |
| per_source | 4 | 4 |
| multi_source | 8+ | 8 |
| no_source | 2 | 2 |
| custom_override | — | 3 |

### Evaluation examples (24)
## Variation: `per_concept`


#### Example 1: `studio_mind_map-001`

- **Variation:** per_concept
- **Tags:** cbse, physics, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Current Electricity

## Ohm's Law
- **V = IR** for ohmic conductors

## Combinations
- **Series:** R_eq adds
- **Parallel:** reciprocal sum

## Microscopic View
- **I = neAv_d** drift relation

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-002`

- **Variation:** per_concept
- **Tags:** neet, biology, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Human Digestion

## Mouth
- **Salivary amylase** on starch

## Stomach
- **HCl + pepsin** for protein

## Small Intestine
- **Villi** absorb nutrients
- Pancreatic **trypsin, lipase**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 3: `studio_mind_map-003`

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

**Mind Map Markdown:**

# Coordination Compounds

## Core Ideas
- **Central metal** + ligands

## Coordination Number
- Count **σ-donor** atoms
- Example **[Fe(CN)6]4−** → CN = 6

## Naming
- **IUPAC:** ligands alphabetical

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 4: `studio_mind_map-004`

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

**Mind Map Markdown:**

# Probability Foundations

## Classical Definition
- **P(E) = favourable / total**

## Rules
- **Addition:** P(A∪B) = P(A)+P(B)−P(A∩B)
- **Independent:** P(A∩B) = P(A)P(B)

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

## Variation: `multi_concept`


#### Example 1: `studio_mind_map-005`

- **Variation:** multi_concept
- **Tags:** cbse, biology, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2. Mitosis: growth/repair, same chromosome number. Meiosis: gametes, halves chromosomes. Prophase I: crossing over.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Energy & Information in Cells

## Photosynthesis
- **Light reaction** → ATP, NADPH (grana)
- **Calvin cycle** fixes CO2 (stroma)

## Cell Division
- **Mitosis** → growth (2n)
- **Meiosis** → gametes (n)
- **Crossing over** in Prophase I

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-006`

- **Variation:** multi_concept
- **Tags:** cbse, chemistry, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Kc=[products]/[reactants] at equilibrium. Le Chatelier: stress shifts to oppose change. Catalyst speeds approach, not K. Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Equilibrium & Electrochemical Cells

## Chemical Equilibrium
- **Kc** at equilibrium
- **Le Chatelier** opposes stress

## Galvanic Cells
- **Anode:** oxidation
- **E°cell = E°cathode − E°anode**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 3: `studio_mind_map-007`

- **Variation:** multi_concept
- **Tags:** cbse, mathematics, scope_mode:multi_concept
- **scope_mode:** multi_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd. Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Binomial & 3D Geometry

## Binomial Theorem
- **Tr+1 = nCr a^(n-r) b^r**

## 3D Lines
- **Direction cosines:** l²+m²+n²=1
- Symmetric line equations

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

## Variation: `per_source`


#### Example 1: `studio_mind_map-008`

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

**Mind Map Markdown:**

# Ray Optics — Lenses

## Lens Equation
- **1/f = 1/v − 1/u**

## Magnification & Power
- **m = v/u**
- **P = 1/f** (f in metres)

## Sign Convention
- Real object **u negative**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-009`

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

**Mind Map Markdown:**

# Molecular Basis of Inheritance

## DNA Structure
- **A–T, G–C** pairing

## Replication
- **Semiconservative** — one old + one new strand

## Expression
- **mRNA** → ribosomes for translation

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 3: `studio_mind_map-010`

- **Variation:** per_source
- **Tags:** cbse, chemistry, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Alkanes CnH2n+2. Markovnikov: H to C with more H. Benzene: delocalized π, extra stability.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Hydrocarbons

## Alkanes
- **CnH2n+2** saturated

## Addition
- **Markovnikov:** H to richer C

## Aromatics
- **Benzene** — delocalized π stability

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 4: `studio_mind_map-011`

- **Variation:** per_source
- **Tags:** cbse, mathematics, scope_mode:per_source
- **scope_mode:** per_source
- **selected_source_count:** 1

**Inputs**

**Context:**

Parabola: focus-directrix equidistance. y²=4ax focus (a,0). e=1 for parabola.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Conic Sections — Parabola

## Definition
- Locus equidistant from **focus** and **directrix**

## Standard Form
- **y² = 4ax** → focus (a,0)
- **Eccentricity e = 1**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

## Variation: `multi_source`


#### Example 1: `studio_mind_map-012`

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

**Mind Map Markdown:**

# Charge Flow & Energy Conversion

## Conductors (Source A)
- **Ohm's law V = IR**
- **ρ = RA/l**

## Electrochemical Cells (Source B)
- **Anode** oxidation
- **E°cell** difference drives flow

## Bridge
- Both describe **directed charge** and **energy transfer**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-013`

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

**Mind Map Markdown:**

# Life Processes — Energy & Reproduction

## Energy Capture (Source A)
- **Photosynthesis** in chloroplasts
- Light → ATP/NADPH → Calvin

## Inheritance Continuity (Source B)
- **Mitosis** maintains 2n
- **Meiosis** halves for gametes

## Integration
- Energy metabolism supports **cell division cycles**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 3: `studio_mind_map-014`

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

**Mind Map Markdown:**

# Counting & Chance

## Probability (Source A)
- **Classical P(E)** ratio
- **Independence** multiplies

## Binomial Expansion (Source B)
- **nCr** coefficients
- **Tr+1** general term

## Link
- Binomial coefficients underpin **probability models**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 4: `studio_mind_map-015`

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

**Mind Map Markdown:**

# Physics Toolkit — Optics & Circuits

## Optics Branch
- **Lens formula** and **m = v/u**

## Circuits Branch
- **V = IR** and **Kirchhoff** rules

## Contrast
- **Geometric optics** vs **electric transport** — both use ratio laws

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 5: `studio_mind_map-016`

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

**Mind Map Markdown:**

# Organism Input & Energy

## Heterotrophic Nutrition
- **Digestive enzymes** and absorption

## Autotrophic Energy
- **Photosynthesis** light and dark reactions

## Theme
- **Matter intake** vs **energy capture** sustain life

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 6: `studio_mind_map-017`

- **Variation:** multi_source
- **Tags:** cbse, chemistry, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.

Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.

**Selected Source Count:**

2

**Expected output**

**Mind Map Markdown:**

# Metals in Chemistry

## Redox Cells
- **Galvanic** electrode roles

## Complex Ions
- **Coordination number** and ligands

## Link
- **Metal centres** appear in both electrochemical and complex forms

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 7: `studio_mind_map-018`

- **Variation:** multi_source
- **Tags:** cbse, mathematics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 2

**Inputs**

**Context:**

Graph ax+by≤c: shade toward origin test point. Feasible region intersection of half-planes. Optimize at vertices.

P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

**Selected Source Count:**

2

**Expected output**

**Mind Map Markdown:**

# Optimization & Uncertainty

## Linear Programming
- **Feasible region** from inequalities

## Probability
- **Event ratios** and rules

## Contrast
- **Deterministic constraints** vs **stochastic outcomes**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

## Variation: `no_source`


#### Example 1: `studio_mind_map-021`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source
- **selected_source_count:** 1

**Inputs**

**Context:**



**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Insufficient source text

## Status
- No excerpt retrieved from selected sources

## Next steps
- Re-index PDF or select sources before regenerating

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-022`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source
- **scope_mode:** no_source
- **selected_source_count:** 2

**Inputs**

**Context:**



**Selected Source Count:**

2

**Expected output**

**Mind Map Markdown:**

# Insufficient source text

## Multi-source selection empty
- **0 chunks** retrieved despite count=2

## Action
- Verify uploads and checkboxes

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

## Variation: `custom_override`


#### Example 1: `studio_mind_map-019`

- **Variation:** custom_override
- **Tags:** cbse, physics, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 3

**Inputs**

**Context:**

W=F·s cos θ. K=½mv². P=W/t. Conservative force: path-independent work. ΔU=-W_conservative.

Torque τ=rF sin θ. τ=Iα. Parallel axis: I=I_cm+Md².

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Selected Source Count:**

3

**Expected output**

**Mind Map Markdown:**

# Mechanics & Electricity Overview

## Work & Energy
- **W = F·s cos θ**, **K = ½mv²**

## Rotation
- **τ = Iα**

## Circuits
- **V = IR**

## Hub Theme
- **Energy transformations** across mechanical and electrical domains

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 2: `studio_mind_map-020`

- **Variation:** custom_override
- **Tags:** cbse, biology, scope_mode:multi_source
- **scope_mode:** multi_source
- **selected_source_count:** 3

**Inputs**

**Context:**

Dicot root: radial vascular bundle. Monocot: polyarch xylem. Casparian strip in endodermis controls flow.

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.

DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.

**Selected Source Count:**

3

**Expected output**

**Mind Map Markdown:**

# Plant Structure & Function

## Anatomy
- **Casparian strip** selective uptake

## Metabolism
- **Photosynthesis** energy capture

## Heredity
- **DNA** replication semantics

## Integration
- Structure supports **transport, energy, and inheritance**

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 3: `studio_mind_map-023`

- **Variation:** custom_override
- **Tags:** cbse, physics, scope_mode:per_concept
- **scope_mode:** per_concept
- **selected_source_count:** 1

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Selected Source Count:**

1

**Expected output**

**Mind Map Markdown:**

# Kirchhoff Laws Only

## Junction Rule
- **ΣI_in = ΣI_out**

## Loop Rule
- **ΣEMF = ΣIR drops**

## Application
- Solve multi-loop circuits

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---

#### Example 4: `studio_mind_map-024`

- **Variation:** custom_override
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

**Mind Map Markdown:**

# Cell Division Comparison Only

## Mitosis
- **2n maintained** — growth/repair

## Meiosis
- **n gametes** — Prophase I crossing over

## User scope
- Map excludes photosynthesis detail despite multi-source excerpt

**Quality Check:** single_hub: pass. grounding: pass. structure: pass.

---
