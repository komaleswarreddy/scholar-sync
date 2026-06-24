## 14. Studio Slide Deck Generator

| Field | Value |
|-------|-------|
| Dataset ID | `studio_slide_deck` |
| Category | Studio |
| Tier | Tier 2 |
| Target examples | 22 |
| Actual examples | 22 |
| Version | 1.2.0 |

**Agent responsibility:** Markdown slide deck with `# Slide N:` headings, 1–7 bullets per slide, story arc ending in conclusion slide. Custom instructions override slide count and focus.

**Audit finding (baseline v1.0.0):** Baseline v1.1.0 used uniform 1–2 bullet stubs per slide. Rebuilt v1.2.0 with production LLM gold via `slide_deck_prompt.j2` + system prompt — variable bullet counts (1–7), story arc, show-don't-tell, and slide-count compliance from custom_instructions.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `per_concept` | Topic-focused custom instructions | 4 |
| `multi_concept` | Full-breadth / all topics in context | 3 |
| `per_source` | Single-source excerpt | 4 |
| `multi_source` | Merged multi-doc context + synthesis | 5 |
| `no_source` | Empty context → generic study-skills branch | 2 |
| `custom_override` | Slide count/language/focus overrides | 4 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **slide_count_match** — Slide count matches custom_instructions.
* **conclusion_present** — Final slide is conclusion with key takeaways.
* **bullet_variance** — 1–7 bullets per slide; not uniform padding.
* **custom_instructions** — Difficulty, language, and focus honored when specified.
* **grounding** — Slide content grounded in context excerpt.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `context`, `custom_instructions`
* Output keys: `slide_deck_markdown`

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
You are an **expert instructional designer and presentation strategist**. Produce a **slide deck outline in Markdown** that **takes the audience on a journey**: concrete, visual-in-language, properly **hierarchical**, and **not** a Word document pasted into slides.

---

## Output contract (non-negotiable)

- Return **ONLY** valid Markdown. **No** code fences, **no** preamble, **no** postscript, **no** JSON.
- **One slide = one top-level heading**, numbered, e.g. `# Slide 1: …`, `# Slide 2: …`.
- Under each heading: **bullet list** for the slide body.
- If the user requested a **language** in Additional instructions, write the **entire** deck in that language.

### Bullet count per slide (important)

- **Per slide: between 1 and 7 bullet lines** (inclusive). **Never more than 7.**
- **Do not** use the same count on every slide (e.g. do **not** pad to 4 bullets everywhere). Use **fewer** bullets when one strong idea is enough; use **more** (up to 6–7) only when the slide truly needs that many distinct beats.
- A **single bullet** may carry a **two-line** thought: either one line ending with `→` or `—` and a short continuation on the next line **indented** as part of the same bullet, **or** a sub-bullet under it. Do not exceed **7 top-level bullet markers** (`-`) per slide.

### Emphasis and hierarchy (Markdown)

- Each slide **title** (heading text) = **short, punchy headline**—the **one** takeaway for that slide, not a chapter label.
- Inside bullets, wrap **the most important term, number, or contrast** in `**bold**` so hierarchy is obvious (e.g. `**Before:** … / **After:** …`, or `**Insulin** → lowers blood glucose …`).
- Prefer **breathing room**: shorter bullets, fewer words per line when possible; avoid dense paragraphs disguised as bullets.

---

## A. Story and flow (CRITICAL)

The deck must feel like it **goes somewhere**, not random topics.

Plan **internally** (do not output the plan), then write slides in roughly this **arc** (adapt to source):

1. **Hook / problem / question** — why this matters or what puzzle you are solving (from the source).
2. **Orient** — minimal framing (avoid a useless “agenda” slide unless it lists **named** sections from **this** material).
3. **Explain step by step** — core ideas in **sequence** learners can follow.
4. **Show with examples** — scenarios, “what it looks like”, mini case moments grounded in the excerpt.
5. **Contrast or mechanism** — before/after, how it works, A vs B where the source supports it.
6. **Conclusion slide (required)** — final slide must be **`# Slide N: …`** with a **conclusion** title and **3–6 bullets** that state **main takeaways**, “so what”, and **what to remember** (specific to the source, not generic “thanks”).

**Forbidden:** slides that feel **disconnected** with no logical link to the previous slide—when you change topic, **one bridging bullet or title phrase** should signal why.

---

## B. Show, don’t tell (CRITICAL)

**Weak (do not write):** “This is important”, “There are many types”, “This affects performance”, “Key concepts include…”, empty “Overview” with no substance.

**Strong (prefer):**

- **What it looks like** — observable behavior, structure, or outcome.
- **How it works** — mechanism in plain steps or cause → effect.
- **Before vs after** or **X vs Y** when the material allows.
- **Real examples or scenarios** from the excerpt (or realistic illustrations tied to the text).

People remember **examples** more than definitions—**prioritize** at least several bullets across the deck that are **scenario- or example-forward**.

---

## C. Grounding and evidence

1. **Source content** is the authority. Do not invent statistics or claims not supported by the excerpt.
2. **Retrieval queries** (if listed) describe retrieval intent—stay aligned; do not paste them as slide titles.
3. If the excerpt is thin, say so briefly on one slide rather than hallucinating.

{% if retrieval_queries_note and retrieval_queries_note.strip() %}
### Retrieval queries used for vector search
{{ retrieval_queries_note }}

{% endif %}
{% if context and context.strip() %}
### Source content (retrieved excerpts)
{{ context }}
{% else %}
### Source content
No source excerpt was provided. Produce a short, coherent generic educational outline on one topic.
{% endif %}

---

## D. Engagement

Include **at least two** moments across the deck (as bullets or a short slide), grounded in the source:

- A **“why” or prediction question** (“Why does …?”, “What would happen if …?”)
- A **comparison** or **what-if** tied to the material

---

## E. Slides vs Word documents

**Rule:** If a slide is only long prose that could live unchanged in a Word doc with no structure, **rewrite** it into **headline + scannable bullets** with **bold** anchors and **concrete** show-don’t-tell content. Slides help people **see** relationships and priorities, not read walls of text.

---

## Additional user instructions

Apply **all** of the following; they override defaults where they conflict.

{% if custom_instructions %}
{{ custom_instructions }}
{% else %}
(No additional user instructions.)
{% endif %}

---

## Pre-output checklist (silent)

- Slide count within user range.
- **Every** slide: **1–7** bullets, **not** a fixed count per slide.
- **Last slide** = **conclusion** with substantive takeaways.
- Story arc: problem/topic → steps → examples → synthesis.
- **Show-don’t-tell**; **bold** key terms/numbers; headlines short and teaching-focused.
- Output **nothing** except the Markdown deck.

Begin the deck now (Markdown only).
```

*Runtime note:* [`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) `StudioService._generate_structured_task()` with slide deck task template.

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


#### Example 1: `studio_slide_deck-001`

- **Variation:** per_concept
- **Tags:** cbse, physics, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

6 slides, medium, focus Ohm's law and series circuits only

**Expected output**

**Slide Deck Markdown:**

# Slide 1: Why Ohm's Law Matters  
- **Understanding electricity** is crucial for modern technology.  
- Ohm's Law connects **voltage**, **current**, and **resistance** in simple terms.  
- What happens when you increase voltage? → **Impact on current** needs exploration.  

# Slide 2: The Basics of Ohm's Law  
- **Ohm's Law**: V = IR  
  - **V**: Voltage (Volts)  
  - **I**: Current (Amperes)  
  - **R**: Resistance (Ohms)  
- This relationship helps predict how **electrical components** behave.  

# Slide 3: Exploring Series Circuits  
- In a **series circuit**, total resistance is the **sum** of individual resistances.  
- Formula: **R_eq = R1 + R2**  
- **Current** remains the same throughout the circuit.  
- What happens to the total resistance if you add more resistors?  

# Slide 4: Visualizing Series Circuits  
- Example: **Three resistors** in series, R1 = 2Ω, R2 = 3Ω, R3 = 5Ω.  
  - Total Resistance: **R_eq = 2 + 3 + 5 = 10Ω**  
- **Voltage drops** across each resistor are proportional to their resistance.  
- **Illustration**: Diagram of a series circuit with labeled components.

# Slide 5: Contrast: Series vs. Parallel  
- In **parallel circuits**, total resistance is found using:  
  - **1/R_eq = 1/R1 + 1/R2**  
- **Current splits** among paths, differing from series circuits.  
- Example: Two resistors in parallel, R1 = 4Ω, R2 = 4Ω.  
  - Total Resistance: **R_eq = 2Ω** → **Lower than individual resistances**.

# Slide 6: Conclusion: Key Takeaways  
- Ohm's Law (V = IR) is fundamental to understanding circuits.  
- Series circuits add resistances; current remains constant.  
- Parallel circuits reduce overall resistance; current divides.  
- Grasping these concepts is essential for effective circuit design.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-002`

- **Variation:** per_concept
- **Tags:** neet, biology, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

**Custom Instructions:**

5 slides, hard NEET style, digestive enzymes only

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Digestive Challenge  
- **How do we break down food?**  
- The **human body** needs enzymes to digest various nutrients.  
- **What happens without them?**  
- Undigested food leads to **malnutrition** and other health issues.  

# Slide 2: Meet the Digestive Enzymes  
- **Salivary Amylase**: begins starch digestion in the mouth.  
- **Pepsin**: activated by **HCl** in the stomach for protein breakdown.  
- **Pancreatic Juice**: contains **trypsin**, **lipase**, and **amylase** for further digestion.  

# Slide 3: How Enzymes Work  
- **Amylase** → breaks down starch into sugars.  
- **Pepsin** → cleaves proteins into peptides.  
- **Lipase** → targets fats, converting them into fatty acids.  
- Absorption occurs in the **small intestine** through villi.  

# Slide 4: Real-World Examples  
- **What if** salivary amylase is absent?  
  - Starch remains undigested → **energy loss**.  
- **Before vs. After** enzyme action:  
  - **Before**: protein molecules intact.  
  - **After**: smaller peptides ready for absorption.  

# Slide 5: Conclusion: Key Takeaways  
- Digestive enzymes are **essential** for nutrient breakdown.  
- Each enzyme has a **specific role** in digestion.  
- Malnutrition can result from enzyme deficiencies.  
- Understanding these processes helps improve **digestive health**.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 3: `studio_slide_deck-003`

- **Variation:** per_concept
- **Tags:** cbse, chemistry, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.

**Custom Instructions:**

4 slides, easy, coordination number concept

**Expected output**

**Slide Deck Markdown:**

# Slide 1: What is Coordination Number?
- **Coordination number** refers to the number of **σ-donor atoms** bonded to a central metal atom.
- Examples include metal complexes like **[Fe(CN)6]4-**, which has a coordination number of **6**.

# Slide 2: How is Coordination Number Determined?
- Identified through the **IUPAC** naming system: 
  - Ligands are listed in **alphabetical order**.
  - Anionic ligands end in **-o**.
- Example: In **[Fe(CN)6]4-**, **CN** is a ligand leading to a coordination number of **6**.

# Slide 3: Why Does Coordination Number Matter?
- Influences the **geometry** of the complex: 
  - Coordination number of **6** typically results in an **octahedral** shape.
- What would happen if the coordination number was **4** instead? 
  - It would likely form a **tetrahedral** or **square planar** geometry.

# Slide 4: Conclusion: Key Takeaways on Coordination Number
- Coordination number is crucial for understanding metal-ligand bonding.
- **6** is a common coordination number seen in many complexes.
- The **geometry** of a complex is directly influenced by its coordination number. 
- Remember: The IUPAC system helps in **identifying ligands** and their order.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 4: `studio_slide_deck-004`

- **Variation:** per_concept
- **Tags:** cbse, mathematics, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.

**Custom Instructions:**

5 slides, medium, independent events focus

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Probability Puzzle
- **What is probability?** → Understanding the chance of events.
- **Why does it matter?** → Impacts decision-making and predictions.
- **Key question:** How do we calculate probabilities effectively?

# Slide 2: Core Concepts of Probability
- **Basic formula:** P(E) = **favourable** outcomes / **total** outcomes.
- **Union of events:** P(A∪B) = P(A) + P(B) - P(A∩B).
- **Independent events:** P(A∩B) = P(A) * P(B).

# Slide 3: Bayes' Theorem Unveiled
- **What is Bayes' Theorem?** → Links prior information with likelihood.
- **Formula:** P(B|A) = (P(A|B) * P(B)) / P(A).
- **Example:** Predicting disease based on test results.

# Slide 4: Real-World Applications
- **Scenario:** Assessing risks in medical testing.
  - **Before:** Only considering test accuracy.
  - **After:** Incorporating prior probabilities for better decisions.
- **What-if question:** What would happen if we ignored prior data?

# Slide 5: Conclusion: Key Takeaways
- **Probability** is essential for informed decision-making.
- Understanding **independence** changes the calculations.
- **Bayes' Theorem** enhances predictions using prior knowledge.
- Key takeaway: Always consider **prior probabilities** when evaluating outcomes.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

## Variation: `multi_concept`


#### Example 1: `studio_slide_deck-005`

- **Variation:** multi_concept
- **Tags:** cbse, biology, scope_mode:multi_concept, production_llm_gold
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2. Mitosis: growth/repair, same chromosome number. Meiosis: gametes, halves chromosomes. Prophase I: crossing over.

**Custom Instructions:**

6 slides, full chapter breadth, no narrow topic

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Puzzle of Photosynthesis
- **How do plants convert light into energy?**
- **Critical process** for life on Earth → sustains ecosystems.
- **Involves** light reactions and dark reactions (Calvin cycle).

# Slide 2: The Light Reaction
- Takes place in **grana** of chloroplasts.
- **Chlorophyll** absorbs light energy → converts to ATP and NADPH.
- **Stomata** regulate gas exchange → CO2 in, O2 out.

# Slide 3: The Calvin Cycle Unveiled
- Occurs in the **stroma** of chloroplasts.
- **Fixes CO2** into glucose → essential for plant growth.
- **Cycles through** several steps → uses ATP and NADPH from light reactions.

# Slide 4: Mitosis vs. Meiosis
- **Mitosis**: growth/repair → maintains same chromosome number.
- **Meiosis**: produces gametes → halves chromosome number.
- **Why does this matter?** → Crucial for genetic diversity.

# Slide 5: Real-World Impact of Photosynthesis
- **Example**: A plant's ability to photosynthesize increases in sunlight.
- **What if** light availability decreases? → Less ATP and glucose production.
- **Crossing over** during meiosis enhances genetic variation in offspring.

# Slide 6: Conclusion: Key Takeaways
- Photosynthesis is essential for energy conversion in plants.
- Light reactions and the Calvin cycle are interconnected.
- Mitosis and meiosis serve different but vital roles in life cycles.
- Understanding these processes is crucial for **ecological balance**.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-006`

- **Variation:** multi_concept
- **Tags:** cbse, chemistry, scope_mode:multi_concept, production_llm_gold
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Kc=[products]/[reactants] at equilibrium. Le Chatelier: stress shifts to oppose change. Catalyst speeds approach, not K. Alkanes CnH2n+2. Markovnikov: H to C with more H. Benzene: delocalized π, extra stability.

**Custom Instructions:**

5 slides, medium, all topics in context

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Equilibrium Puzzle
- **What happens** at equilibrium? 
- **Kc = [products]/[reactants]** is the ratio at equilibrium.
- If disturbed, how does the system respond? 
- **Le Chatelier's principle**: stress shifts to oppose change.
- **Why does this matter?** → Understanding equilibrium is crucial in chemistry.

# Slide 2: Stress and Response
- **Stressors** can include changes in concentration, temperature, or pressure.
- System reactions:
  - **Increase in reactants** → shifts right to produce more products.
  - **Increase in temperature** → endothermic direction favored.
- **Predict** the outcomes: What if we change one variable?

# Slide 3: Role of Catalysts
- **Catalysts** speed up reactions but do not change Kc.
- They **lower activation energy**, allowing faster equilibrium.
- **Example**: Adding a catalyst to a reaction mixture reduces the time to reach equilibrium.
- **What would happen** if no catalyst is used?

# Slide 4: Structure of Alkanes and Benzene
- **Alkanes**: General formula **CnH2n+2**—simple hydrocarbons.
- **Benzene**: Contains **delocalized π electrons**, providing extra stability.
- **Comparison**: Alkanes vs. Benzene → different structures, different stability.
- **Visualize**: Draw the structural formulas to see differences.

# Slide 5: Conclusion: Key Takeaways
- **Equilibrium** is dynamic: Kc defines the balance.
- **Le Chatelier's principle** helps predict system responses.
- Catalysts accelerate reactions without altering equilibrium constants.
- Understand the **structure**: Alkanes vs. Benzene impacts stability.
- **Remember**: Predicting outcomes relies on recognizing stressors and system behavior.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 3: `studio_slide_deck-007`

- **Variation:** multi_concept
- **Tags:** cbse, mathematics, scope_mode:multi_concept, production_llm_gold
- **scope_mode:** multi_concept

**Inputs**

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd. Graph ax+by≤c: shade toward origin test point. Feasible region intersection of half-planes. Optimize at vertices.

**Custom Instructions:**

5 slides, medium, full breadth

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Challenge of Expansion  
- **What is the expansion** of (a+b)^n?  
- Understanding the **general term** Tr+1 = nCr a^(n-r) b^r  
- **Why it matters:** essential for combinatorial problems  

# Slide 2: Core Concepts Unveiled  
- **nCr**: the number of combinations of n items taken r at a time  
- **Middle term** shifts depending on whether n is **even** or **odd**  
- **Visualization**: Graph ax + by ≤ c shows feasible regions  

# Slide 3: Real-World Application  
- Consider the **feasible region** as a **project planning** model  
  - Tasks vs. resources represented in the graph  
- **What happens** when you change parameters?  
  - Adjusting c affects the **intersection of half-planes**  
- **Example**: Optimizing project outcomes at vertices  

# Slide 4: Contrast in Problem Solving  
- **Before:** Relying solely on linear models  
- **After:** Integrating (a+b)^n for **complex scenarios**  
  - More flexible with multiple variables  
- **What-if scenario:** If we increase n, how does the outcome change?  

# Slide 5: Conclusion: Key Takeaways  
- The **expansion** of (a+b)^n is foundational in combinatorics  
- Understanding **nCr** enhances problem-solving capabilities  
- **Feasible regions** provide visual insights into optimization  
- Integration of these concepts leads to **better decision-making**

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

## Variation: `per_source`


#### Example 1: `studio_slide_deck-008`

- **Variation:** per_source
- **Tags:** cbse, physics, scope_mode:per_source, production_llm_gold
- **scope_mode:** per_source

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

**Custom Instructions:**

6 slides, CBSE Ray Optics chapter

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Puzzle of Ray Optics
- **How do rays behave** when they encounter lenses?
- Understanding **light behavior** is crucial for optics.
- **Key questions**:
  - Why does light bend?
  - How do we calculate image properties?

# Slide 2: The Basics of Lenses
- **Lens formula:** `1/f = 1/v - 1/u` 
  - Relates focal length (**f**) to image distance (**v**) and object distance (**u**).
- **Magnification formula:** `m = v/u`
  - Measures image size relative to the object.
- **Power (P):** `P = 1/f`
  - Indicates lens strength in **metres**.

# Slide 3: Real-World Applications
- **Example:** A camera lens focusing light → creates a sharp image.
- **Scenario:** Using lenses in **glasses** for clear vision.
- **Real object (u)** is always **negative** — why it matters in calculations.

# Slide 4: Understanding Ray Diagrams
- **Ray through optical center** remains **undeviated**.
- **Three key rays** to draw:
  - Ray parallel to the axis → refracts through the focal point.
  - Ray through the center → continues straight.
  - Ray through the focal point → refracts parallel to the axis.
- Visualizing helps in understanding **image formation**.

# Slide 5: Before and After Lenses
- **Before:** Light rays diverging from a point source.
- **After:** Rays converge at a point to form a clear image.
- **What if:** What happens if the focal length changes?
  - Longer focal length → **larger** images.

# Slide 6: Conclusion and Key Takeaways
- **Ray optics** is essential for understanding lens behavior.
- **Formulas** help predict outcomes in real-world scenarios.
- **Key concepts**:
  - Importance of **focal length** and **magnification**.
  - Ray diagrams are critical for visualizing optics.
- Mastering these concepts enhances our ability to design optical devices.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-009`

- **Variation:** per_source
- **Tags:** cbse, biology, scope_mode:per_source, production_llm_gold
- **scope_mode:** per_source

**Inputs**

**Context:**

DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.

**Custom Instructions:**

5 slides, molecular inheritance

**Expected output**

**Slide Deck Markdown:**

# Slide 1: What is Molecular Inheritance?  
- **Molecular inheritance** refers to how genetic information is passed through **DNA**.  
- Key players: **A-T** and **G-C** pairing ensures accurate replication.  

# Slide 2: The Process of DNA Replication  
- **Semiconservative replication** → each new DNA strand contains one original and one new strand.  
- Steps involve **unzipping** the DNA and **building** new strands using base pairing.  
- This ensures fidelity in genetic information transfer.  

# Slide 3: mRNA's Role in Inheritance  
- **mRNA** carries the genetic code from DNA to ribosomes.  
- This process is crucial for **protein synthesis**, which affects traits and functions.  
- Example: A mutation in mRNA can lead to a **defective protein** → changing organism traits.  

# Slide 4: Why is Molecular Inheritance Important?  
- Understanding molecular inheritance helps explain **genetic diseases**.  
- **What would happen if** DNA replication were faulty?  
- Consequences include **cancer** or inherited disorders.  

# Slide 5: Conclusion: Key Takeaways  
- Molecular inheritance is foundational to **genetics**.  
- DNA replication is **semiconservative**, ensuring accuracy.  
- **mRNA** translates genetic code to produce proteins.  
- Missteps in this process can lead to serious health implications.  
- Understanding these concepts is essential for advancements in **genetic research**.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 3: `studio_slide_deck-010`

- **Variation:** per_source
- **Tags:** cbse, chemistry, scope_mode:per_source, production_llm_gold
- **scope_mode:** per_source

**Inputs**

**Context:**

Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.

**Custom Instructions:**

4 slides, galvanic cells

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Power of Galvanic Cells
- **Why** are galvanic cells important?  
  — They convert **chemical energy** into **electrical energy**.
- Key components:  
  - **Anode**: site of oxidation  
  - **Cathode**: site of reduction  
- Essential for batteries and electrochemical devices.

# Slide 2: How Galvanic Cells Operate
- **E°cell** formula:  
  - **E°cell** = **E°cathode** - **E°anode**
- Electrons flow from anode to cathode → producing current.
- **Oxidation** and **reduction** reactions drive the process.

# Slide 3: Real-World Examples
- Common example: **Zinc-Copper galvanic cell**  
  - Zinc oxidizes at the anode → releases electrons.  
  - Copper reduces at the cathode → accepts electrons.
- **Nernst equation**: relates EMF to concentration → influences cell performance.
- **What would happen if** we used different metals?  
  - Change in voltage and efficiency based on selected materials.

# Slide 4: Conclusion: Key Takeaways
- Galvanic cells are crucial for energy conversion.  
- Understanding **E°cell** is essential for predicting cell behavior.  
- Real-life applications are found in batteries and sensors.  
- **Predictive questions** can enhance understanding of material choices.  
- Remember: **Oxidation** at anode, **reduction** at cathode!

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 4: `studio_slide_deck-011`

- **Variation:** per_source
- **Tags:** cbse, mathematics, scope_mode:per_source, production_llm_gold
- **scope_mode:** per_source

**Inputs**

**Context:**

Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.

**Custom Instructions:**

5 slides, 3D geometry

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Challenge of 3D Geometry  
- Understanding **3D shapes** is crucial for real-world applications.  
- **Why does** knowing about direction cosines and skew lines matter?  
- These concepts help us navigate **spatial relationships** effectively.  

# Slide 2: Key Elements of 3D Geometry  
- **Direction cosines**: Represented as **l, m, n** — key for defining angles with axes.  
- The equation **l² + m² + n² = 1** ensures valid direction cosines.  
- **Line equation**: Expressed as **(x-x1)/a = (y-y1)/b = (z-z1)/c** for parametric representation.  

# Slide 3: Visualizing Skew Lines  
- **Skew lines**: Non-intersecting and non-parallel lines in 3D space.  
- The **shortest distance** between skew lines is found using the **cross product**.  
- **Example**: Imagine two roads that never meet but are not parallel.  

# Slide 4: Contrasting Directions in 3D  
- **Before**: Traditional 2D geometry lacks depth — only height and width.  
- **After**: 3D geometry introduces **depth** — height, width, and length create complex relationships.  
- **What if** we ignored the third dimension? Spatial understanding would be severely limited.  

# Slide 5: Conclusion: Key Takeaways  
- **Direction cosines** are essential for understanding angles in 3D.  
- The line equation allows for precise **spatial representation**.  
- **Skew lines** demonstrate unique relationships between lines in space.  
- Grasping these concepts enhances **spatial reasoning** and real-world applications.  
- Remember: **3D geometry** shapes our perception of the world around us.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

## Variation: `multi_source`


#### Example 1: `studio_slide_deck-012`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source, production_llm_gold
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Current Electricity] Ohm's law V=IR; resistivity ρ=RA/l.

[Source B — Electrochemistry] Galvanic cell: anode oxidation; E°cell=E°cathode-E°anode.

**Custom Instructions:**

6 slides, integrate electricity and electrochemistry sources

**Expected output**

**Slide Deck Markdown:**

# Slide 1: Why Understanding Electricity Matters
- **Current** impacts our daily lives → from **charging devices** to powering homes.
- **Ohm's Law**: V = IR → fundamental for electrical engineering.
- Misunderstandings can lead to **inefficient designs** or **safety hazards**.

# Slide 2: Key Concepts of Electricity
- **Voltage (V)**: electric potential difference.
- **Current (I)**: flow of electric charge.
- **Resistance (R)**: opposition to current flow.
- **Resistivity (ρ)**: material property affecting resistance → ρ = RA/l.

# Slide 3: Exploring Electrochemistry Fundamentals
- **Galvanic Cell**: converts chemical energy to electrical energy.
- **Anode**: site of **oxidation**; where electrons are released.
- **E°cell**: Standard cell potential → E°cell = E°cathode - E°anode.
- Predict: What happens if anode material changes? 

# Slide 4: Real-World Applications
- **Ohm's Law in Action**: Designing circuits → ensuring devices function properly.
- **Galvanic Cells**: Used in batteries → powering everyday devices like phones.
- Compare: **Using resistors** vs. **direct current** in circuits.

# Slide 5: Mechanisms Behind Electrical and Electrochemical Processes
- **Before**: High resistance → low current flow.
- **After**: Adjusting resistance increases current → enhances device performance.
- **How**: Changing materials in a galvanic cell affects E°cell → impacts voltage output.

# Slide 6: Conclusion: Key Takeaways
- Understanding **Ohm's Law** is essential for effective circuit design.
- Knowledge of **galvanic cells** enables advancements in energy storage.
- Mastering these concepts leads to improved **safety** and **efficiency** in electrical applications.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-013`

- **Variation:** multi_source
- **Tags:** cbse, biology, scope_mode:multi_source, production_llm_gold
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Photosynthesis] Light reaction in grana; Calvin cycle in stroma.

[Source B — Cell division] Mitosis maintains chromosome number; meiosis halves for gametes.

**Custom Instructions:**

5 slides, photosynthesis + cell division

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Energy Puzzle
- **How do plants** convert sunlight into energy?  
- The process of **photosynthesis** is key — it fuels life on Earth.  
- **Why does this matter?** Understanding it helps us grasp ecosystems.  

# Slide 2: The Photosynthesis Process
- **Light reactions** occur in the **grana** — they capture sunlight.  
- **Calvin cycle** takes place in the **stroma** — it uses CO2 to form sugars.  
- Sequence: Light → Energy → Chemical bonds.  

# Slide 3: Cell Division Explained
- **Mitosis** ensures **chromosome number** is maintained — critical for growth.  
- **Meiosis** halves the chromosome number for gametes — essential for reproduction.  
- **What if** mitosis didn’t occur properly? → Cells would be dysfunctional.  

# Slide 4: Real-World Examples
- In photosynthesis, plants like **sunflowers** convert sunlight effectively.  
- During cell division, a **failure in meiosis** can lead to genetic disorders like Down syndrome.  
- **Contrast:** Healthy division vs. errors leading to mutations.  

# Slide 5: Conclusion: Key Insights
- Photosynthesis transforms sunlight into **chemical energy**.  
- Mitosis and meiosis have distinct roles in **cellular processes**.  
- Understanding these mechanisms enhances our grasp of **life sciences**.  
- Remember: **Energy flow** and **genetic integrity** are fundamental to life.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 3: `studio_slide_deck-014`

- **Variation:** multi_source
- **Tags:** cbse, mathematics, scope_mode:multi_source, production_llm_gold
- **scope_mode:** multi_source

**Inputs**

**Context:**

[Source A — Probability] P(E)=favourable/total; P(A∩B)=P(A)P(B) if independent.

[Source B — Binomial] Tr+1=nCr a^(n-r) b^r in (a+b)^n expansion.

**Custom Instructions:**

5 slides, probability + binomial

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Power of Probability  
- **Understanding probability** helps us navigate uncertainty.  
- **Why does it matter?**  
  - It influences decision-making in daily life.  
  - **Example:** Predicting weather patterns, sports outcomes.  

# Slide 2: Core Probability Concepts  
- **Probability Formula:** P(E) = **favourable outcomes** / **total outcomes**  
- **Independent Events:** P(A∩B) = P(A)P(B)  
  - **Example:** Tossing two coins—each coin's outcome is independent.  
- **Visualize:** Probability as a **fraction** of possible outcomes.  

# Slide 3: Binomial Distribution Explained  
- **What is it?** A model for experiments with **two outcomes** (success/failure).  
- **Formula:** Tr+1 = nCr a^(n-r) b^r  
  - **a:** Probability of success, **b:** Probability of failure.  
- **Real-World Application:** Quality control in manufacturing—pass/fail tests.  

# Slide 4: Examples in Action  
- **Scenario 1:** Flipping a coin 10 times—calculate the probability of getting exactly 5 heads.  
  - Use binomial distribution for precise predictions.  
- **Scenario 2:** Drawing cards from a deck—what's the chance of drawing an Ace?  
  - P(Ace) = **4** (favourable) / **52** (total) → **7.7%** chance.  

# Slide 5: Conclusion: Key Takeaways  
- Probability provides a **framework** for decision-making under uncertainty.  
- Binomial distribution models outcomes with **clear parameters**.  
- Understand the **formulas** to leverage them effectively in real-life scenarios.  
- **Remember:** Probability is everywhere—from games to serious predictions!

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 4: `studio_slide_deck-015`

- **Variation:** multi_source
- **Tags:** cbse, physics, scope_mode:multi_source, production_llm_gold
- **scope_mode:** multi_source

**Inputs**

**Context:**

Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.

Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.

**Custom Instructions:**

7 slides, optics and circuits selected sources

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Power of Optics and Circuits  
- How do **optics** and **electric circuits** interplay?  
- Understanding these concepts is crucial for modern technology.  
- What happens when light and electricity meet?  

# Slide 2: Key Optical Formulas  
- **Lens Formula:** 1/f = 1/v - 1/u  
  - **f** = focal length, **v** = image distance, **u** = object distance  
- **Magnification:** m = v/u  
- **Power of Lens:** P = 1/f (with **f** in metres)  

# Slide 3: Exploring Circuit Basics  
- **Ohm's Law:** V = IR  
- **Resistivity Formula:** ρ = RA/l  
  - **R** = resistance, **A** = cross-sectional area, **l** = length  
- **Series Circuits:** R_eq = R1 + R2  
- **Parallel Circuits:** 1/R_eq = 1/R1 + 1/R2  

# Slide 4: Real-World Applications of Optics  
- **Cameras** use lens formulas to focus light → delivers sharp images.  
- **Eyeglasses** adjust focal lengths for vision correction.  
- **Projectors** employ magnification for larger displays.  

# Slide 5: Circuit Scenarios  
- **Series vs. Parallel:**  
  - **Series:** Same current, voltage divides → simple circuits like **Christmas lights**.  
  - **Parallel:** Same voltage, current divides → used in **home wiring** for safety.  
- **Kirchhoff's Laws:**  
  - Sum of currents at a junction: I_in = I_out  

# Slide 6: Why Does This Matter?  
- **What if** we didn't understand these principles?  
  - Technology failures, poor designs, safety hazards.  
- Predict the outcome of changing resistance in a circuit.  
  - Higher resistance → **lower current** → affects performance.  

# Slide 7: Conclusion: Key Takeaways  
- **Optics** and **circuits** are interlinked in technology.  
- Mastering formulas enables practical applications in real life.  
- Understanding **series** and **parallel** systems is essential for safety and efficiency.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 5: `studio_slide_deck-016`

- **Variation:** multi_source
- **Tags:** neet, biology, scope_mode:multi_source, production_llm_gold
- **scope_mode:** multi_source

**Inputs**

**Context:**

Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.

Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.

**Custom Instructions:**

6 slides, NEET cross-topic

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Role of Digestion
- **Why does digestion matter?**  
  It’s essential for nutrient absorption and energy production.
- **Key players:**  
  Includes enzymes like **amylase**, **pepsin**, and **lipase**.
- **The journey begins:**  
  Starts in the mouth, continues through the stomach, and ends in the small intestine.

# Slide 2: Digestion Process Overview
- **Mouth:**  
  Salivary **amylase** breaks down carbohydrates.
- **Stomach:**  
  **HCl** activates **pepsin** for protein digestion.
- **Pancreas:**  
  Releases **trypsin**, **lipase**, and **amylase** into the small intestine for further breakdown.
- **Final stage:**  
  Nutrients are absorbed in the small intestine's **villi**.

# Slide 3: Energy Conversion in Plants
- **Light reaction:**  
  Occurs in **grana**, producing **ATP** and **NADPH**.
- **Calvin cycle:**  
  Takes place in the **stroma**, fixing **CO2** into sugars.
- **Chlorophyll's role:**  
  Absorbs light energy, essential for photosynthesis.

# Slide 4: Real-World Application
- **Scenario:**  
  What happens if **amylase** is deficient?  
  - Impaired carbohydrate digestion leads to energy shortages.
- **Comparison:**  
  How does digestion differ in animals vs. plants?  
  - Animals consume nutrients directly; plants synthesize them via photosynthesis.

# Slide 5: Mechanisms of Exchange
- **Stomata function:**  
  Control **CO2** and **O2** exchange during photosynthesis.
- **Absorption processes:**  
  Villi increase surface area for nutrient uptake in the small intestine.
- **Before and after:**  
  - **Before:** Nutrients remain undigested.  
  - **After:** Nutrients are efficiently absorbed into the bloodstream.

# Slide 6: Conclusion: Key Takeaways
- Digestion is vital for nutrient absorption and energy.
- Enzymes like **amylase**, **pepsin**, and **lipase** play crucial roles.
- Photosynthesis involves **light reactions** and the **Calvin cycle**.
- Understanding these processes enhances knowledge of biology and health.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

## Variation: `no_source`


#### Example 1: `studio_slide_deck-017`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source, production_llm_gold
- **scope_mode:** no_source

**Inputs**

**Context:**



**Custom Instructions:**

4 slides, general study skills — no source

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Challenge of Effective Study Skills
- **Why study well?** → Crucial for **academic success** and lifelong learning.
- Many students struggle with **time management** and focus.
- Common pitfalls include **procrastination** and ineffective techniques.
- **What if** you could change your study habits? 

# Slide 2: Steps to Improve Your Study Skills
- **Set clear goals** → Define what you want to achieve.
- **Create a study schedule** — Allocate specific times for each subject.
- Use **active learning strategies**: summarizing, questioning, and teaching others.
- **Break down material** into manageable chunks for better retention.

# Slide 3: Real-Life Study Techniques
- **Pomodoro Technique** → Study for **25 minutes**, then take a **5-minute break**.
- **Mind mapping** — Visualize connections between concepts.
- **Flashcards** for spaced repetition → Enhance memory of key terms.
- **Study groups** — Share insights and clarify doubts together.

# Slide 4: Conclusion: Key Takeaways for Effective Studying
- **Effective study skills** lead to better learning outcomes.
- Set **clear goals** and stick to a structured schedule.
- Incorporate **active techniques** to engage with the material.
- Regularly assess your progress and adapt methods as needed.
- Remember: **Consistency** is key to mastering study skills.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-018`

- **Variation:** no_source
- **Tags:** edge_case, scope_mode:no_source, production_llm_gold
- **scope_mode:** no_source

**Inputs**

**Context:**



**Custom Instructions:**

3 slides, minimal generic science outline

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Mystery of Photosynthesis
- **Why does** photosynthesis matter?  
  — It fuels nearly all life on Earth.
- **Key process:** Converts **solar energy** into **chemical energy**.
- Plants, algae, and some bacteria are **photosynthetic** organisms.
- The **equation:** 
  - **6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂**.

# Slide 2: Steps of Photosynthesis
- **Light-dependent reactions:**  
  — Occur in the **thylakoid membranes** of chloroplasts.
- **Key outputs:** 
  - **ATP** and **NADPH** produced from light energy.
- **Calvin cycle:**  
  — Takes place in the **stroma** of chloroplasts.
- **Carbon fixation** converts CO₂ into glucose.
- **Energy flow:** 
  - Light energy → chemical energy → stored in glucose.

# Slide 3: Conclusion: Photosynthesis Unlocked
- **Photosynthesis is vital** for life on Earth.
- It transforms **solar energy** into usable forms for organisms.
- Key steps include **light reactions** and the **Calvin cycle**.
- Understanding this process helps grasp **ecosystem dynamics**.  
  — Essential for **food webs** and **carbon cycling**.  
- **Remember:** Without photosynthesis, life as we know it wouldn’t exist!

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

## Variation: `custom_override`


#### Example 1: `studio_slide_deck-019`

- **Variation:** custom_override
- **Tags:** cbse, physics, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

Torque τ=rF sin θ. τ=Iα. Parallel axis: I=I_cm+Md².

**Custom Instructions:**

8 slides, hard difficulty, include torque numerical examples

**Expected output**

**Slide Deck Markdown:**

# Slide 1: What is Torque?
- **Torque (τ)** → a measure of rotational force
- Formula: τ = **rF sin θ**
- **r** = distance from pivot → lever arm
- **F** = applied force
- **θ** = angle between force and lever arm

# Slide 2: Why Torque Matters
- Essential in **mechanical systems** → affects motion
- Key in **engineering** and **physics** applications
- Example: **Wrenches** amplify force → make tasks easier
- Understanding torque helps in **designing** efficient machines

# Slide 3: The Torque Equation Explained
- **τ = Iα** → relates torque to angular acceleration
- **I** = moment of inertia → object's resistance to rotation
- **α** = angular acceleration → change in rotational speed
- **Understanding** the relationship is crucial for dynamic systems

# Slide 4: Real-World Example: Torque in Action
- **Example 1:** Car engine → torque affects acceleration
  - Higher torque = **faster** acceleration
- **Example 2:** Door hinges → requires torque to open
  - Positioning of handle changes applied torque

# Slide 5: Calculating Torque: A Numerical Example
- **Example Calculation:**
  - **Force (F)** = 10 N, **r** = 0.5 m, **θ** = 90°
  - τ = 0.5 * 10 * sin(90°) = **5 N·m**
- **Implications** of results in mechanical design

# Slide 6: Parallel Axis Theorem
- **I = I_cm + Md²** → calculating moment of inertia
- **I_cm** = moment of inertia about center of mass
- **M** = mass of object, **d** = distance from center of mass
- Critical for **complex systems** and multi-body analysis

# Slide 7: Why Does Torque Change?
- **What if**: Changing the angle θ affects torque
  - **θ = 0°** → τ = 0 (no rotation)
  - **θ = 90°** → maximum torque
- Predict how torque varies with different lever arm lengths

# Slide 8: Conclusion: Key Takeaways
- Torque is essential for understanding **rotational dynamics**
- Key formulas: τ = rF sin θ and τ = Iα
- Real-world applications enhance **mechanical efficiency**
- Calculating torque aids in **design decisions** across industries

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 2: `studio_slide_deck-020`

- **Variation:** custom_override
- **Tags:** cbse, chemistry, scope_mode:per_concept, production_llm_gold
- **scope_mode:** per_concept

**Inputs**

**Context:**

Tollens' test: silver mirror with aldehydes, not ketones. C=O undergoes nucleophilic addition.

**Custom Instructions:**

5 slides, explain in simple English — aldehyde tests only

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Mystery of Aldehydes
- **Why do we care about aldehydes?**  
  They are crucial in organic chemistry and are identified through specific tests.
- **The challenge:**  
  Distinguishing aldehydes from other compounds like ketones can be tricky.

# Slide 2: Introduction to Tollens' Test
- **What is Tollens' Test?**  
  A chemical test used to identify **aldehydes**.
- **Key reagent:**  
  **Silver nitrate** solution in ammonia forms **Tollens' reagent**.
- **Reaction outcome:**  
  Produces a **silver mirror** when aldehydes are present.

# Slide 3: How the Test Works
- **Nucleophilic addition**:  
  Aldehydes have a **C=O** group that reacts with Tollens' reagent.
- **Reaction steps:**  
  1. Aldehyde interacts with Tollens' reagent.  
  2. Silver ions are reduced to metallic silver.  
  3. A shiny silver mirror forms on the test container.

# Slide 4: Aldehydes vs. Ketones
- **Aldehydes** → **Positive Tollens' Test**:  
  Produce the silver mirror.
- **Ketones** → **Negative Tollens' Test**:  
  Do not react with Tollens' reagent.
- **Why does this matter?**  
  Helps chemists identify compounds in unknown mixtures.

# Slide 5: Conclusion: Key Takeaways
- **Tollens' Test** is essential for identifying **aldehydes**.
- A **silver mirror** confirms the presence of aldehydes, not ketones.
- Understanding the reaction helps in organic synthesis and analysis.  
- Remember the **nucleophilic addition** mechanism for clarity.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 3: `studio_slide_deck-021`

- **Variation:** custom_override
- **Tags:** cbse, mathematics, scope_mode:per_source, production_llm_gold
- **scope_mode:** per_source

**Inputs**

**Context:**

(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd.

**Custom Instructions:**

3 slides, thin excerpt — minimum viable deck

**Expected output**

**Slide Deck Markdown:**

# Slide 1: The Challenge of Expansion
- Understanding the **expansion of (a + b)^n** is crucial in algebra.
- How do we determine the **general term** in this expansion? 
- The formula uses **nCr** to find **Tr+1**: 
  - **Tr+1** = nCr * a^(n-r) * b^r.
- Why does the **middle term** depend on whether **n** is **even** or **odd**?
  
# Slide 2: Step-by-Step Breakdown
- **Step 1:** Identify **n** — the exponent in the expression.
- **Step 2:** Calculate **nCr** for each term needed.
- **Step 3:** Apply the formula: 
  - Plug in **a** and **b** values.
- **Example:** For **n=3**, the expansion is:
  - (a + b)^3 = a^3 + 3a^2b + 3ab^2 + b^3.

# Slide 3: Key Takeaways
- The expansion of (a + b)^n reveals patterns through **nCr**.
- The **general term** formula is essential for complex problems.
- **Middle term significance** depends on whether **n** is even or odd:
  - Even n → single middle term.
  - Odd n → two middle terms.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---

#### Example 4: `studio_slide_deck-022`

- **Variation:** custom_override
- **Tags:** cbse, biology, scope_mode:multi_concept, production_llm_gold
- **scope_mode:** multi_concept

**Inputs**

**Context:**

Dicot root: radial vascular bundle. Monocot: polyarch xylem. Casparian strip in endodermis controls flow.

**Custom Instructions:**

6 slides, whole chapter revision — root anatomy

**Expected output**

**Slide Deck Markdown:**

# Slide 1: Why Root Anatomy Matters
- **Roots** are essential for **water** and **nutrient** uptake.
- Understanding the **structure** can enhance **agricultural practices**.
- What happens when root systems fail? → **Crop yield** declines.

# Slide 2: The Basics of Root Structure
- Two main types: **Dicots** and **Monocots**.
- **Dicot roots** feature a **radial vascular bundle** — organized for efficiency.
- **Monocot roots** have **polyarch xylem** — multiple xylem strands for support.

# Slide 3: The Role of the Casparian Strip
- Located in the **endodermis** — a critical barrier.
- Controls the flow of **water** and **nutrients** into the vascular system.
- **Why does it matter?** → Prevents harmful substances from entering.

# Slide 4: Real-World Application of Root Anatomy
- **Example:** In **drought conditions**, deep-rooted plants thrive.
- **Comparison:** Shallow roots vs deep roots → access to moisture levels.
- **What would happen if** roots were poorly structured? → Increased vulnerability.

# Slide 5: Mechanisms of Nutrient Uptake
- Roots use **osmosis** and **active transport** for nutrient absorption.
- **Before:** Limited nutrient access in poor soil → 
- **After:** Enhanced root structure improves **uptake efficiency**.

# Slide 6: Conclusion: Key Takeaways on Root Anatomy
- Roots are vital for **sustaining plant life** and productivity.
- Understanding root types helps in **crop management**.
- The **Casparian strip** is crucial for selective nutrient flow.
- Efficient root systems can combat **environmental stresses** effectively.

**Quality Check:** slide_count_match: pass. conclusion_present: pass. bullet_variance: pass. custom_instructions: pass. grounding: pass. production_llm_gold: pass.

---
