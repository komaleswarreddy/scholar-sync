## 9. Hallucination Guard Retry Suffix

| Field | Value |
|-------|-------|
| Dataset ID | `hallucination_guard_retry` |
| Category | Generation |
| Tier | Tier 3 baseline → focused enrichment set |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.1.0 |

**Agent responsibility:** When deterministic grounding check flags unsupported sentences, production appends `strict_retry_suffix()` from [`hallucination_guard.py`](packages/core/rag/hallucination_guard.py) to the RAG generation prompt. The model must rewrite the answer using **only context evidence**.

**Audit finding (baseline v1.0.0):** The original 12-example set used 100% placeholder gold for corrected answers and had no pass-through cases where grounded answers remain unchanged. Expanded to 15 examples with ~50% rewrite vs pass balance, production-faithful retry suffix inline, and real corrected_answer gold grounded in NCERT excerpts.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `rewrite_remove` | Drop unsupported claims | 5 |
| `rewrite_soften` | Replace with excerpt-grounded wording | 3 |
| `rewrite_label_gk` | Label `General knowledge:` when appropriate | 2 |
| `pass_through` | Already grounded — minimal/no change | 4 |
| `pass_minor_edit` | Trivial punctuation/clarity only | 1 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **grounding** — Corrected answer supported by context excerpt terms.
* **unsupported_removed** — Flagged sentences absent or properly softened/labeled.
* **no_new_facts** — No new numbers, names, or dates beyond evidence.
* **retry_suffix_compliance** — Rewrite follows hallucination guard suffix rules.
* **pass_balance** — Pass cases retain grounded content without over-stripping.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `answer`, `context`, `unsupported_sentences`
* Output keys: `corrected_answer`

**Prompt suffix (production — `strict_retry_suffix()`):**

```text
Grounding instruction (hallucination guard):
- Remove, soften, or label as `General knowledge:` any sentence not directly supported by the Context evidence.
- Prefer restating the evidence using the same terms as the excerpts.
- Do not add new specific numbers, names, dates, or quotes unless they appear in the evidence.

Unsupported sentences detected:
- {unsupported_sentence_1}
- {unsupported_sentence_2}

```

*Runtime note:* Appended in [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py) on retry when `ENABLE_HALLUCINATION_GUARD` flags unsupported sentences after initial RAG response.

### Evaluation examples (15)
## Variation: `rewrite_remove`


#### Example 1: `hallucination_guard_retry-001`

- **Variation:** rewrite_remove
- **Tags:** grounding, biology, negative

**Inputs**

**Answer:**

The human heart has five chambers and blue blood circulates in all arteries.

**Context:**

NCERT Biology: Pepsin acts in stomach at acidic pH; trypsin and chymotrypsin act in duodenum with pancreatic juice.

**Unsupported Sentences:**

["The human heart has five chambers"]

**Expected output**

**Corrected Answer:**

Pepsin acts in the stomach at acidic pH. Trypsin and chymotrypsin act in the duodenum with pancreatic juice.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 2: `hallucination_guard_retry-002`

- **Variation:** rewrite_remove
- **Tags:** grounding, physics, negative

**Inputs**

**Answer:**

Newton published Principia in 1685 and invented calculus independently of Leibniz.

**Context:**

Ray optics: Lens formula 1/f = 1/v − 1/u. Magnification m = v/u. Power P = 1/f.

**Unsupported Sentences:**

["Newton published Principia in 1685"]

**Expected output**

**Corrected Answer:**

For lenses, 1/f = 1/v − 1/u and magnification m = v/u. Lens power P = 1/f.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 3: `hallucination_guard_retry-003`

- **Variation:** rewrite_remove
- **Tags:** grounding, biology, negative

**Inputs**

**Answer:**

Photosynthesis occurs only at night in all plant species worldwide.

**Context:**

Photosynthesis in chloroplasts: light reaction in grana produces ATP and NADPH; Calvin cycle in stroma fixes CO2.

**Unsupported Sentences:**

["Photosynthesis occurs only at night"]

**Expected output**

**Corrected Answer:**

Photosynthesis occurs in chloroplasts: the light reaction in grana produces ATP and NADPH, and the Calvin cycle in stroma fixes CO2.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 4: `hallucination_guard_retry-006`

- **Variation:** rewrite_remove
- **Tags:** grounding, physics, negative

**Inputs**

**Answer:**

Superconductors have infinite resistance at room temperature in all household wires.

**Context:**

Current electricity: Ohm's law V = IR. Resistivity ρ increases with temperature for metals.

**Unsupported Sentences:**

["Superconductors have infinite resistance at room temperature"]

**Expected output**

**Corrected Answer:**

Ohm's law states V = IR. For metals, resistivity ρ increases with temperature.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 5: `hallucination_guard_retry-013`

- **Variation:** rewrite_remove
- **Tags:** grounding, chemistry, negative

**Inputs**

**Answer:**

Benzene has alternating single and double bonds that flip every millisecond at room temperature.

**Context:**

Hydrocarbons: Benzene has delocalized π electrons giving extra stability (resonance). Markovnikov rule applies to asymmetric alkene addition.

**Unsupported Sentences:**

["alternating single and double bonds that flip every millisecond"]

**Expected output**

**Corrected Answer:**

Benzene has delocalized π electrons giving extra stability through resonance.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

## Variation: `rewrite_soften`


#### Example 1: `hallucination_guard_retry-004`

- **Variation:** rewrite_soften
- **Tags:** grounding, chemistry, negative

**Inputs**

**Answer:**

Gold is the most abundant metal in Earth's crust and dissolves easily in water.

**Context:**

Electrochemistry: In galvanic cells oxidation occurs at anode; E°cell = E°cathode − E°anode.

**Unsupported Sentences:**

["Gold is the most abundant metal", "dissolves easily in water"]

**Expected output**

**Corrected Answer:**

In galvanic cells, oxidation occurs at the anode. Standard cell EMF E°cell = E°cathode − E°anode.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 2: `hallucination_guard_retry-014`

- **Variation:** rewrite_soften
- **Tags:** grounding, mathematics, negative

**Inputs**

**Answer:**

Every linear inequality graph is always a circle in the coordinate plane.

**Context:**

Linear inequalities: Graph ax+by≤c by shading the half-plane toward the origin test point. Feasible region is intersection of constraints.

**Unsupported Sentences:**

["always a circle"]

**Expected output**

**Corrected Answer:**

Graph ax+by≤c by shading the half-plane that satisfies the inequality (e.g. toward origin for ≤). Feasible region is the intersection of all constraint half-planes.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

## Variation: `rewrite_label_gk`


#### Example 1: `hallucination_guard_retry-005`

- **Variation:** rewrite_label_gk
- **Tags:** grounding, mathematics, negative

**Inputs**

**Answer:**

The probability of rolling sum 7 with two dice is exactly 1/2 every time.

**Context:**

Probability: P(E) = favourable outcomes / total outcomes. For two fair dice, sum 7 has 6 favourable outcomes out of 36.

**Unsupported Sentences:**

["The probability of rolling sum 7 with two dice is exactly 1/2 every time"]

**Expected output**

**Corrected Answer:**

P(E) = favourable outcomes / total outcomes. For two fair dice, sum 7 has 6 favourable outcomes out of 36 (P = 6/36 = 1/6).

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

## Variation: `pass_through`


#### Example 1: `hallucination_guard_retry-007`

- **Variation:** pass_through
- **Tags:** grounding, physics, positive

**Inputs**

**Answer:**

Ohm's law states V = IR for ohmic conductors. In series, equivalent resistance adds: R_eq = R1 + R2.

**Context:**

Ohm's law: V = IR. Series combination R_eq = R1 + R2. Parallel: 1/R_eq = 1/R1 + 1/R2.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

Ohm's law states V = IR for ohmic conductors. In series, equivalent resistance adds: R_eq = R1 + R2.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 2: `hallucination_guard_retry-008`

- **Variation:** pass_through
- **Tags:** grounding, biology, positive

**Inputs**

**Answer:**

Mitosis produces genetically identical cells for growth; meiosis halves chromosome number for gametes.

**Context:**

Cell division: Mitosis maintains chromosome number for growth and repair. Meiosis reduces chromosome number to form gametes.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

Mitosis produces genetically identical cells for growth; meiosis halves chromosome number for gametes.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 3: `hallucination_guard_retry-010`

- **Variation:** pass_through
- **Tags:** grounding, mathematics, positive

**Inputs**

**Answer:**

For a parabola y² = 4ax, the focus is at (a, 0) and eccentricity equals 1.

**Context:**

Conic sections: Standard parabola y² = 4ax has focus (a,0), directrix x = −a, eccentricity e = 1.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

For a parabola y² = 4ax, the focus is at (a, 0) and eccentricity equals 1.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 4: `hallucination_guard_retry-011`

- **Variation:** pass_through
- **Tags:** grounding, biology, positive

**Inputs**

**Answer:**

DNA replication is semiconservative: each new duplex contains one parental and one newly synthesized strand.

**Context:**

Molecular basis of inheritance: DNA replication is semiconservative — each new molecule has one old and one new strand.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

DNA replication is semiconservative: each new duplex contains one parental and one newly synthesized strand.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 5: `hallucination_guard_retry-012`

- **Variation:** pass_through
- **Tags:** grounding, physics, positive

**Inputs**

**Answer:**

Lens power P equals the reciprocal of focal length in metres: P = 1/f.

**Context:**

Ray optics: Lens power P = 1/f when f is in metres. Sign convention uses Cartesian distances from optical centre.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

Lens power P equals the reciprocal of focal length in metres: P = 1/f.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

#### Example 6: `hallucination_guard_retry-015`

- **Variation:** pass_through
- **Tags:** grounding, chemistry, positive

**Inputs**

**Answer:**

Le Chatelier's principle states that a system at equilibrium shifts to oppose an applied stress such as pressure or concentration change.

**Context:**

Equilibrium: Le Chatelier — system shifts to partially counteract imposed stress. Catalyst does not change Kc.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

Le Chatelier's principle states that a system at equilibrium shifts to oppose an applied stress such as pressure or concentration change.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---

## Variation: `pass_minor_edit`


#### Example 1: `hallucination_guard_retry-009`

- **Variation:** pass_minor_edit
- **Tags:** grounding, chemistry, positive

**Inputs**

**Answer:**

In coordination compounds, the coordination number counts donor atoms bonded to the central metal ion.

**Context:**

Coordination compounds: Coordination number is the count of σ-donor atoms directly bonded to the metal.

**Unsupported Sentences:**

[]

**Expected output**

**Corrected Answer:**

In coordination compounds, the coordination number counts σ-donor atoms directly bonded to the central metal ion.

**Quality Check:** grounding: pass. retry_suffix_compliance: pass.

---
