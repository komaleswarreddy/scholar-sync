## 8. Chat Summarizer Agent

| Field | Value |
|-------|-------|
| Dataset ID | `chat_summarizer` |
| Category | Generation |
| Tier | Tier 2 |
| Target examples | 20 |
| Actual examples | 20 |
| Version | 1.1.0 |

**Agent responsibility:** Compress a multi-turn tutor chat into structured Markdown for later review. Operates on **conversation transcript only** — no source PDF retrieval. Must not invent facts beyond the chat.

**Audit finding (baseline v1.0.0):** The original 20-example set rotated only two transcript templates ~15×, causing tag/subject mismatches and insufficient section variety (formulas, analogies, open questions). Rebuilt with 20 unique NCERT-grounded transcripts, locked variation taxonomy, full inline production prompt, and gold summaries that omit empty sections per prompt contract.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `short_transcript` | 2–3 turn chats; minimal sections | 4 |
| `medium_transcript` | 4–6 turns; standard section mix | 8 |
| `long_multi_topic` | 8+ turns; open questions / analogies | 2 |
| `numerical_formula` | Formulas in `## Definitions / formulas` | 3 |
| `neet_exam_framing` | NEET/CBSE drill tone in transcript | 3 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **structure** — Required `##` headings present when content exists; bullets not wall-of-text.
* **no_hallucination** — Summary facts appear in conversation transcript only.
* **section_omit_empty** — Empty optional sections omitted per prompt contract.
* **concise** — Summary 2–4 sentences; key points 3–7 bullets.
* **tag_alignment** — Tags reflect conversation subject and exam framing.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `old_conversation`
* Output keys: `summary_markdown`

**Prompt template (production):**

```jinja2
You are a study-focused tutor. Summarize the chat for a student so it is easy to review later.

## Output requirements (strict)
- Output **Markdown** only.
- Use the following section headings exactly (omit a section if it would be empty):
  - `## Summary`
  - `## Key points from the chat`
  - `## Definitions / formulas (if any)`
  - `## Examples / analogies used`
  - `## Open questions / next steps`
- Keep it concise:
  - `## Summary`: 2–4 short sentences (not a wall of text).
  - `## Key points from the chat`: 3–7 bullets, one idea per bullet.
  - Other sections: up to 3–6 bullets total across all remaining sections.
- Do not invent facts. Only include what appears in the conversation.
- If the chat is very short or repetitive, still produce a clean structure with fewer bullets.

## Conversation history

{{ old_conversation }}

## Summary
```

*Runtime note:* Loaded from [`packages/core/memory/chat_summarizer.py`](packages/core/memory/chat_summarizer.py) when conversation history exceeds token threshold in chat memory pipeline.

### Evaluation examples (20)
## Variation: `short_transcript`


#### Example 1: `chat_summarizer-001`

- **Variation:** short_transcript
- **Tags:** cbse, physics, source_pdf:leph103

**Inputs**

**Old Conversation:**

User: What is Ohm's law?
Assistant: V equals I times R for ohmic conductors at constant temperature.
User: Quick numerical?
Assistant: With R=5 Ω and I=3 A, voltage V=15 V.

**Expected output**

**Summary Markdown:**

## Summary

Reviewed Ohm's law and a quick numerical using V=IR.

## Key points from the chat

- Ohm's law: V = IR at constant temperature
- Example: 3 A through 5 Ω gives 15 V

## Definitions / formulas (if any)

- V = IR

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 2: `chat_summarizer-006`

- **Variation:** short_transcript
- **Tags:** cbse, mathematics, source_pdf:lemh207

**Inputs**

**Old Conversation:**

User: P(drawing ace from deck)?
Assistant: 4 favourable / 52 total ≈ 1/13.
User: Independent events?
Assistant: P(A∩B)=P(A)P(B) when outcomes don't affect each other.
User: Addition rule?
Assistant: P(A∪B)=P(A)+P(B)−P(A∩B).

**Expected output**

**Summary Markdown:**

## Summary

Practised basic probability rules with a card example.

## Key points from the chat

- Classical P = favourable/total (ace ≈ 1/13)
- Independent: P(A∩B)=P(A)P(B)
- Addition: P(A∪B)=P(A)+P(B)−P(A∩B)

## Examples / analogies used

- Standard deck ace draw

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 3: `chat_summarizer-009`

- **Variation:** short_transcript
- **Tags:** cbse, mathematics, source_pdf:kemh111

**Inputs**

**Old Conversation:**

User: Parabola definition?
Assistant: Locus equidistant from focus and directrix.
User: Standard form y²=4ax?
Assistant: Focus at (a,0), directrix x=−a.
User: Eccentricity of parabola?
Assistant: e = 1 always.

**Expected output**

**Summary Markdown:**

## Summary

Defined parabola, standard form, and eccentricity.

## Key points from the chat

- Parabola: equidistant from focus and directrix
- y²=4ax → focus (a,0), directrix x=−a
- Eccentricity e = 1

## Definitions / formulas (if any)

- y² = 4ax

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 4: `chat_summarizer-016`

- **Variation:** short_transcript
- **Tags:** cbse, mathematics, source_pdf:kemh107

**Inputs**

**Old Conversation:**

User: (x+y)^5 middle term?
Assistant: For n=5, middle term is T3 with coefficient 5C2=10.
User: General term?
Assistant: Tr+1 = nCr x^(n−r) y^r.
User: When n even?
Assistant: Single middle term at r = n/2.

**Expected output**

**Summary Markdown:**

## Summary

Practised binomial expansion middle term and general term.

## Key points from the chat

- n=5 middle term T3, coeff 5C2=10
- Tr+1 = nCr x^(n−r) y^r
- Even n: single middle at r=n/2

## Definitions / formulas (if any)

- Tr+1 = nCr x^(n−r) y^r

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

## Variation: `medium_transcript`


#### Example 1: `chat_summarizer-004`

- **Variation:** medium_transcript
- **Tags:** cbse, physics, source_pdf:leph201

**Inputs**

**Old Conversation:**

User: Sign of u for real object?
Assistant: Real object distance u is negative in Cartesian sign convention.
User: Lens formula?
Assistant: 1/f = 1/v − 1/u.
User: Magnification?
Assistant: m = v/u; negative m means inverted image.
User: Ray through optical centre?
Assistant: Undeviated straight-line path.

**Expected output**

**Summary Markdown:**

## Summary

Covered lens sign convention, formula, and magnification.

## Key points from the chat

- Real object: u negative
- Lens formula 1/f = 1/v − 1/u
- m = v/u; negative m → inverted image
- Ray through optical centre passes undeviated

## Definitions / formulas (if any)

- 1/f = 1/v − 1/u
- m = v/u

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 2: `chat_summarizer-005`

- **Variation:** medium_transcript
- **Tags:** cbse, chemistry, source_pdf:lech105

**Inputs**

**Old Conversation:**

User: What is coordination number?
Assistant: Number of donor atoms directly bonded to central metal ion.
User: Example with CN=6?
Assistant: [Fe(CN)6]4− has coordination number six.
User: Ligand?
Assistant: Ion or molecule attached to metal via coordinate bond.

**Expected output**

**Summary Markdown:**

## Summary

Defined coordination number and ligands with an example complex.

## Key points from the chat

- Coordination number counts σ-donor atoms on metal
- [Fe(CN)6]4− has CN = 6
- Ligands attach via coordinate bonds

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 3: `chat_summarizer-008`

- **Variation:** medium_transcript
- **Tags:** cbse, chemistry, source_pdf:kech203

**Inputs**

**Old Conversation:**

User: Alkane general formula?
Assistant: CnH2n+2; saturated hydrocarbons.
User: Markovnikov rule?
Assistant: In asymmetric alkene addition, H goes to C with more H atoms.
User: Benzene stability?
Assistant: Delocalized π electrons give extra stability (resonance).

**Expected output**

**Summary Markdown:**

## Summary

Reviewed alkane formula, Markovnikov rule, and benzene stability.

## Key points from the chat

- Alkanes: CnH2n+2
- Markovnikov: H adds to C with more H
- Benzene stability from delocalized π electrons

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 4: `chat_summarizer-010`

- **Variation:** medium_transcript
- **Tags:** cbse, biology, source_pdf:lebo105

**Inputs**

**Old Conversation:**

User: Semiconservative means?
Assistant: Each new DNA has one parental and one new strand.
User: Enzyme for unwinding?
Assistant: Helicase separates strands at replication fork.
User: Leading vs lagging?
Assistant: Continuous synthesis on leading; Okazaki fragments on lagging strand.

**Expected output**

**Summary Markdown:**

## Summary

Explained semiconservative replication and strand synthesis.

## Key points from the chat

- Each new DNA: one old + one new strand
- Helicase unwinds at fork
- Leading continuous; lagging Okazaki fragments

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 5: `chat_summarizer-011`

- **Variation:** medium_transcript
- **Tags:** cbse, chemistry, source_pdf:lech103

**Inputs**

**Old Conversation:**

User: Anode in galvanic cell?
Assistant: Oxidation occurs; electrons leave anode.
User: Standard hydrogen electrode?
Assistant: Reference with E° = 0.00 V by convention.
User: When does cell stop?
Assistant: When equilibrium reached — net reaction ceases.

**Expected output**

**Summary Markdown:**

## Summary

Reviewed galvanic cell electrodes and equilibrium stopping condition.

## Key points from the chat

- Anode: oxidation; electrons leave
- SHE reference E° = 0
- Cell stops at equilibrium

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 6: `chat_summarizer-013`

- **Variation:** medium_transcript
- **Tags:** cbse, biology, source_pdf:kebo106

**Inputs**

**Old Conversation:**

User: Dicot vs monocot root?
Assistant: Dicot: radial vascular bundle; monocot: polyarch xylem.
User: Casparian strip?
Assistant: Suberin band in endodermis controls apoplastic flow.
User: Why important?
Assistant: Forces selective symplastic uptake into stele.

**Expected output**

**Summary Markdown:**

## Summary

Compared root anatomy features and Casparian strip function.

## Key points from the chat

- Dicot vs monocot vascular arrangement differs
- Casparian strip in endodermis has suberin
- Forces selective uptake into stele

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 7: `chat_summarizer-014`

- **Variation:** medium_transcript
- **Tags:** cbse, physics, source_pdf:keph105

**Inputs**

**Old Conversation:**

User: Work by variable force?
Assistant: W = ∫F·dx; graphically area under F-x curve.
User: Conservative force?
Assistant: Work independent of path; e.g. gravity.
User: Potential energy relation?
Assistant: ΔU = −W_conservative.

**Expected output**

**Summary Markdown:**

## Summary

Connected work, conservative forces, and potential energy.

## Key points from the chat

- Variable work W = ∫F·dx
- Conservative force: path-independent work
- ΔU = −W_conservative

## Definitions / formulas (if any)

- W = ∫F·dx

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 8: `chat_summarizer-017`

- **Variation:** medium_transcript
- **Tags:** cbse, chemistry, source_pdf:kech106

**Inputs**

**Old Conversation:**

User: Kc definition?
Assistant: Ratio of product to reactant molar concentrations at equilibrium.
User: Increase pressure on N2+3H2⇌2NH3?
Assistant: Shifts toward fewer moles — forward to NH3.
User: Catalyst effect on K?
Assistant: No change to K; speeds attainment only.

**Expected output**

**Summary Markdown:**

## Summary

Applied equilibrium constant and Le Chatelier to ammonia synthesis.

## Key points from the chat

- Kc uses molar concentrations at equilibrium
- Higher pressure favors NH3 (fewer moles)
- Catalyst does not change K

## Definitions / formulas (if any)

- Kc = [products]/[reactants]

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

## Variation: `long_multi_topic`


#### Example 1: `chat_summarizer-019`

- **Variation:** long_multi_topic
- **Tags:** cbse, mathematics, source_pdf:kemh105

**Inputs**

**Old Conversation:**

User: Graph 2x+y≤6?
Assistant: Boundary line 2x+y=6; shade toward origin for ≤.
User: Feasible region?
Assistant: Intersection of all constraint half-planes.
User: Corner point method?
Assistant: Evaluate objective function at vertices of feasible polygon.

**Expected output**

**Summary Markdown:**

## Summary

Graphed linear inequality and corner-point optimization idea.

## Key points from the chat

- Shade toward origin for 2x+y≤6
- Feasible region = intersection of constraints
- Optimize at polygon vertices

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 2: `chat_summarizer-020`

- **Variation:** long_multi_topic
- **Tags:** cbse, physics, source_pdf:leph103

**Inputs**

**Old Conversation:**

User: Define drift velocity.
Assistant: Average velocity of electrons under electric field in conductor.
User: Relation to current?
Assistant: I = neAv_d.
User: Resistivity temperature dependence?
Assistant: For metals ρ increases with T due to more collisions.
User: Series circuit rule?
Assistant: Same current through each element.
User: Parallel rule?
Assistant: Same potential across branches.
User: Kirchhoff loop law?
Assistant: Algebraic sum of EMFs equals sum of IR drops.
User: Open question?
Assistant: We should practice wheatstone bridge next.
User: Analogy?
Assistant: Water flow in pipes parallels current in wires.

**Expected output**

**Summary Markdown:**

## Summary

Extended current electricity review from drift velocity through Kirchhoff laws.

## Key points from the chat

- Drift velocity v_d; I = neAv_d
- Metal resistivity rises with temperature
- Series: same I; parallel: same V
- Loop law: ΣEMF = ΣIR

## Definitions / formulas (if any)

- I = neAv_d

## Examples / analogies used

- Water flow in pipes parallels current

## Open questions / next steps

- Practice Wheatstone bridge problems

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

## Variation: `numerical_formula`


#### Example 1: `chat_summarizer-007`

- **Variation:** numerical_formula
- **Tags:** cbse, physics, source_pdf:keph106

**Inputs**

**Old Conversation:**

User: Torque definition?
Assistant: τ = r × F; magnitude τ = rF sin θ.
User: Moment of inertia role?
Assistant: Rotational analog of mass; τ = Iα.
User: Parallel axis theorem?
Assistant: I = I_cm + Md² shifts axis parallel to CM axis.

**Expected output**

**Summary Markdown:**

## Summary

Discussed torque, moment of inertia, and parallel axis theorem.

## Key points from the chat

- τ = rF sin θ
- τ = Iα analog of F = ma
- I = I_cm + Md² for parallel axis shift

## Definitions / formulas (if any)

- τ = r × F

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 2: `chat_summarizer-012`

- **Variation:** numerical_formula
- **Tags:** cbse, mathematics, source_pdf:lemh205

**Inputs**

**Old Conversation:**

User: Direction cosines?
Assistant: cos α, cos β, cos γ of line with axes; l²+m²+n²=1.
User: Equation of line in 3D?
Assistant: (x−x1)/a = (y−y1)/b = (z−z1)/c.
User: Shortest distance skew lines?
Assistant: Formula using cross product of direction vectors.

**Expected output**

**Summary Markdown:**

## Summary

Covered direction cosines and 3D line equations.

## Key points from the chat

- Direction cosines satisfy l²+m²+n²=1
- Symmetric line: (x−x1)/a = (y−y1)/b = (z−z1)/c
- Skew line distance uses cross product

## Definitions / formulas (if any)

- l² + m² + n² = 1

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 3: `chat_summarizer-015`

- **Variation:** numerical_formula
- **Tags:** cbse, chemistry, source_pdf:lech203

**Inputs**

**Old Conversation:**

User: Tollens' test?
Assistant: Ag+ reduced to silver mirror by aldehydes.
User: Ketones with Tollens?
Assistant: No reaction — distinguishes aldehyde vs ketone.
User: Nucleophilic addition?
Assistant: C=O polarized; nucleophile attacks carbonyl carbon.

**Expected output**

**Summary Markdown:**

## Summary

Used Tollens' test to distinguish aldehydes from ketones.

## Key points from the chat

- Tollens' gives silver mirror with aldehydes
- Ketones do not react with Tollens'
- C=O undergoes nucleophilic addition

## Examples / analogies used

- Silver mirror as visual test

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

## Variation: `neet_exam_framing`


#### Example 1: `chat_summarizer-002`

- **Variation:** neet_exam_framing
- **Tags:** neet, biology, source_pdf:kebo110

**Inputs**

**Old Conversation:**

User: Light vs dark reaction location?
Assistant: Light reaction in grana; Calvin cycle in stroma of chloroplast.
User: What enters Calvin cycle?
Assistant: CO2 is fixed using ATP and NADPH from light reactions.
User: NEET one-liner?
Assistant: Photosynthesis converts light energy to chemical energy in glucose.

**Expected output**

**Summary Markdown:**

## Summary

Located photosynthesis stages and linked them to NEET revision.

## Key points from the chat

- Light reaction in grana; Calvin cycle in stroma
- CO2 fixed using ATP and NADPH
- Converts light energy to chemical energy in glucose

## Open questions / next steps

- Revise C4 vs C3 pathways separately

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 2: `chat_summarizer-003`

- **Variation:** neet_exam_framing
- **Tags:** neet, biology, source_pdf:kebo107

**Inputs**

**Old Conversation:**

User: Where does protein digestion start?
Assistant: Stomach — pepsin works in acidic HCl medium.
User: Pancreatic enzymes?
Assistant: Trypsin, chymotrypsin, lipase, amylase enter duodenum via pancreatic juice.
User: Absorption site?
Assistant: Small intestine villi absorb most nutrients.

**Expected output**

**Summary Markdown:**

## Summary

Traced protein digestion and enzyme locations for NEET.

## Key points from the chat

- Pepsin starts protein digestion in acidic stomach
- Pancreatic trypsin, lipase, amylase act in duodenum
- Villi in small intestine absorb nutrients

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---

#### Example 3: `chat_summarizer-018`

- **Variation:** neet_exam_framing
- **Tags:** cbse, biology, source_pdf:kebo110

**Inputs**

**Old Conversation:**

User: Mitosis vs meiosis purpose?
Assistant: Mitosis growth/repair; meiosis gamete formation halves chromosome number.
User: Prophase I feature?
Assistant: Crossing over between homologous chromosomes.
User: Analogy you used?
Assistant: Mitosis like photocopy; meiosis like shuffling deck for variety.

**Expected output**

**Summary Markdown:**

## Summary

Contrasted mitosis and meiosis with crossing over highlight.

## Key points from the chat

- Mitosis for growth; meiosis for gametes
- Prophase I: crossing over

## Examples / analogies used

- Mitosis = photocopy; meiosis = shuffled deck

**Quality Check:** structure: pass. no_hallucination: pass. concise: pass. tag_alignment: pass.

---
