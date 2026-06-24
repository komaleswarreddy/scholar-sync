## Variation: `broad_topic`

#### Example 1: `scope_narrower-001`

- **Variation:** broad_topic
- **Tags:** cbse, biology, source_pdf_kebo106

**Inputs**

**Query:** Explain everything about anatomy of flowering plants.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- anatomy
- flowering plants
- root
- stem
- leaf
- tissue organization

**Focused Query:** anatomy flowering plants root stem leaf tissue organization fundamentals

**Max Chunks:** 11

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Broad chapter request narrowed to foundational plant-structure concepts.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, intent_lock_check

---

#### Example 2: `scope_narrower-002`

- **Variation:** broad_topic
- **Tags:** cbse, chemistry, source_pdf_kech104

**Inputs**

**Query:** Teach me the entire chemical equilibrium chapter.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- chemical equilibrium
- equilibrium constant
- Kc
- reversible reaction
- Le Chatelier principle

**Focused Query:** chemical equilibrium constant Kc reversible reactions Le Chatelier principle

**Max Chunks:** 10

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Full chapter reduced to core equilibrium retrieval targets.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, intent_lock_check

---

#### Example 3: `scope_narrower-003`

- **Variation:** broad_topic
- **Tags:** cbse, mathematics, source_pdf_kemh105

**Inputs**

**Query:** I want to understand all of linear inequalities.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- linear inequalities
- one variable
- two variables
- graphical solution
- solution region

**Focused Query:** linear inequalities one variable two variables graphical solution methods

**Max Chunks:** 9

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Broad topic narrowed to standard inequality-solving methods.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, intent_lock_check

---

#### Example 4: `scope_narrower-004`

- **Variation:** broad_topic
- **Tags:** cbse, physics, source_pdf_keph105

**Inputs**

**Query:** Explain work, energy, and power from scratch.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- work-energy theorem
- kinetic energy
- work
- power
- energy conservation

**Focused Query:** work energy theorem kinetic energy power definitions fundamentals

**Max Chunks:** 9

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Multi-topic request narrowed to foundational work-energy-power concepts.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, intent_lock_check

---

#### Example 5: `scope_narrower-005`

- **Variation:** broad_topic
- **Tags:** cbse, biology, source_pdf_lebo105

**Inputs**

**Query:** Cover the whole chapter on molecular basis of inheritance.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- DNA structure
- DNA replication
- genetic code
- molecular inheritance
- central dogma

**Focused Query:** DNA structure replication genetic code molecular basis of inheritance

**Max Chunks:** 10

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Chapter-level scope reduced to core inheritance mechanisms.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, intent_lock_check

---

## Variation: `multi_part`

#### Example 6: `scope_narrower-006`

- **Variation:** multi_part
- **Tags:** cbse, biology, source_pdf_lebo105

**Inputs**

**Query:** Explain DNA structure, replication, transcription, and translation.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- central dogma
- DNA structure
- DNA replication
- transcription
- translation

**Focused Query:** central dogma DNA structure replication transcription translation flow

**Max Chunks:** 9

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Multi-concept query consolidated under central-dogma retrieval target.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, relationship_preservation

---

#### Example 7: `scope_narrower-007`

- **Variation:** multi_part
- **Tags:** cbse, chemistry, source_pdf_kech106

**Inputs**

**Query:** Explain ionic bonding, covalent bonding, VSEPR theory, and hybridization.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- ionic bonding
- covalent bonding
- VSEPR theory
- hybridization
- molecular geometry

**Focused Query:** ionic covalent bonding VSEPR hybridization molecular shape progression

**Max Chunks:** 10

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Bond-type to molecular-shape hierarchy preserved in one focused scope.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, relationship_preservation

---

#### Example 8: `scope_narrower-008`

- **Variation:** multi_part
- **Tags:** cbse, mathematics, source_pdf_lemh205

**Inputs**

**Query:** Teach me parabola, ellipse, hyperbola, and their eccentricities.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- conic sections
- parabola
- ellipse
- hyperbola
- eccentricity

**Focused Query:** conic sections parabola ellipse hyperbola eccentricity definitions

**Max Chunks:** 9

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Shared eccentricity concept unifies multi-curve request.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, relationship_preservation

---

#### Example 9: `scope_narrower-009`

- **Variation:** multi_part
- **Tags:** cbse, physics, source_pdf_leph201

**Inputs**

**Query:** Explain reflection, refraction, total internal reflection, and optical instruments.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- reflection
- refraction
- total internal reflection
- optical instruments
- ray optics

**Focused Query:** reflection refraction total internal reflection optical instruments ray optics principles

**Max Chunks:** 10

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Ray-optics phenomena grouped under governing principles.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, relationship_preservation

---

#### Example 10: `scope_narrower-010`

- **Variation:** multi_part
- **Tags:** cbse, biology, source_pdf_kebo110

**Inputs**

**Query:** Explain enzymes, hormones, digestion, and metabolism.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- enzymes
- hormones
- digestion
- metabolism
- biochemical regulation

**Focused Query:** enzymes hormones digestion metabolism biological regulation

**Max Chunks:** 9

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Physiological processes consolidated into one retrieval scope.

**Evaluators:** json_schema, max_chunks_range, scope_precision_check, relationship_preservation

---

## Variation: `exam_oriented`

#### Example 11: `scope_narrower-011`

- **Variation:** exam_oriented
- **Tags:** cbse, biology, source_pdf_lebo105

**Inputs**

**Query:** NEET PYQ on DNA replication and semiconservative model.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- DNA replication
- semiconservative model
- replication fork
- Meselson-Stahl

**Focused Query:** DNA replication mechanism semiconservative model replication fork

**Max Chunks:** 7

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Exam framing removed; concept scope preserved.

**Evaluators:** json_schema, max_chunks_range, terminology_normalization, scope_precision_check

---

#### Example 12: `scope_narrower-012`

- **Variation:** exam_oriented
- **Tags:** cbse, chemistry, source_pdf_lech103

**Inputs**

**Query:** JEE Advanced question on Nernst equation and cell potential.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- Nernst equation
- cell potential
- electrode potential
- electrochemical cell

**Focused Query:** Nernst equation electrode potential cell potential concentration dependence

**Max Chunks:** 6

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. JEE framing stripped to electrochemistry retrieval terms.

**Evaluators:** json_schema, max_chunks_range, terminology_normalization, scope_precision_check

---

#### Example 13: `scope_narrower-013`

- **Variation:** exam_oriented
- **Tags:** cbse, mathematics, source_pdf_kemh107

**Inputs**

**Query:** CBSE board exam derivation of binomial theorem.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- binomial theorem
- binomial expansion
- general term
- derivation

**Focused Query:** binomial theorem statement derivation prerequisites general term formula

**Max Chunks:** 6

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Board-exam context removed; derivation scope retained.

**Evaluators:** json_schema, max_chunks_range, terminology_normalization, scope_precision_check

---

#### Example 14: `scope_narrower-014`

- **Variation:** exam_oriented
- **Tags:** cbse, physics, source_pdf_leph201

**Inputs**

**Query:** Board exam derivation of lens maker's formula.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- lens maker formula
- focal length
- refractive index
- thin lens

**Focused Query:** lens maker formula derivation focal length refractive index thin lens

**Max Chunks:** 6

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Exam framing normalized to formula-derivation retrieval scope.

**Evaluators:** json_schema, max_chunks_range, terminology_normalization, scope_precision_check

---

#### Example 15: `scope_narrower-015`

- **Variation:** exam_oriented
- **Tags:** cbse, chemistry, source_pdf_kech104

**Inputs**

**Query:** MCQ practice for chemical equilibrium.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- chemical equilibrium
- equilibrium constant
- Le Chatelier principle
- reversible reaction

**Focused Query:** chemical equilibrium principles equilibrium constant Le Chatelier reversible reaction

**Max Chunks:** 7

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Assessment format removed; equilibrium concepts isolated.

**Evaluators:** json_schema, max_chunks_range, terminology_normalization, scope_precision_check

---

## Variation: `numerical`

#### Example 16: `scope_narrower-016`

- **Variation:** numerical
- **Tags:** cbse, biology, source_pdf_kebo107

**Inputs**

**Query:** A pedigree shows the trait in every generation affecting both sexes equally. Is it autosomal dominant?
**Transcript Section:** 

**Expected output**

**Key Terms:**
- pedigree analysis
- autosomal dominant
- inheritance pattern
- Mendelian genetics

**Focused Query:** pedigree analysis autosomal dominant inheritance pattern identification criteria

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Case details reduced to governing inheritance-pattern rules.

**Evaluators:** json_schema, max_chunks_range, formula_identification, scope_precision_check

---

#### Example 17: `scope_narrower-017`

- **Variation:** numerical
- **Tags:** cbse, chemistry, source_pdf_lech103

**Inputs**

**Query:** Calculate the cell potential at 298 K when concentration of zinc ions is 0.1 M using the Nernst equation.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- Nernst equation
- cell potential
- concentration cell
- electrode potential

**Focused Query:** Nernst equation cell potential concentration dependence zinc ions

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Numerical setup narrowed to Nernst-equation application.

**Evaluators:** json_schema, max_chunks_range, formula_identification, scope_precision_check

---

#### Example 18: `scope_narrower-018`

- **Variation:** numerical
- **Tags:** cbse, mathematics, source_pdf_kemh111

**Inputs**

**Query:** Find the probability of getting exactly two heads in five tosses of a fair coin.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- binomial distribution
- probability
- binomial formula
- independent trials

**Focused Query:** binomial probability distribution exactly two successes five fair coin tosses

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Word problem reduced to binomial-probability formula retrieval.

**Evaluators:** json_schema, max_chunks_range, formula_identification, scope_precision_check

---

#### Example 19: `scope_narrower-019`

- **Variation:** numerical
- **Tags:** cbse, physics, source_pdf_keph105

**Inputs**

**Query:** A block slides down a frictionless incline of height 5 m. Find its velocity at the bottom.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- conservation of mechanical energy
- kinetic energy
- potential energy
- incline motion

**Focused Query:** conservation mechanical energy block sliding frictionless incline final velocity

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Numerical narrowed to energy-conservation principle.

**Evaluators:** json_schema, max_chunks_range, formula_identification, scope_precision_check

---

#### Example 20: `scope_narrower-020`

- **Variation:** numerical
- **Tags:** cbse, physics, source_pdf_keph106

**Inputs**

**Query:** A solid disc of mass 2 kg and radius 0.5 m rotates at 10 rad/s. Find its rotational kinetic energy.
**Transcript Section:** 

**Expected output**

**Key Terms:**
- rotational kinetic energy
- moment of inertia
- angular velocity
- solid disc

**Focused Query:** rotational kinetic energy formula moment of inertia angular velocity solid disc

**Max Chunks:** 4

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Problem setup reduced to rotational KE formula retrieval.

**Evaluators:** json_schema, max_chunks_range, formula_identification, scope_precision_check

---

## Variation: `conversational_follow_up`

#### Example 21: `scope_narrower-021`

- **Variation:** conversational_follow_up
- **Tags:** cbse, biology, source_pdf_lebo105

**Inputs**

**Query:** Explain that part again.
**Transcript Section:**

Student: Why does DNA replicate in a semiconservative manner?

Assistant: Explained the Meselson-Stahl experiment and semiconservative replication.

**Expected output**

**Key Terms:**
- semiconservative replication
- DNA replication
- Meselson-Stahl
- replication mechanism

**Focused Query:** semiconservative DNA replication Meselson-Stahl experiment mechanism

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Coreference resolved to semiconservative replication without scope expansion.

**Evaluators:** json_schema, max_chunks_range, coreference_resolution, scope_precision_check

---

#### Example 22: `scope_narrower-022`

- **Variation:** conversational_follow_up
- **Tags:** cbse, chemistry, source_pdf_kech104

**Inputs**

**Query:** Can you repeat the formula you mentioned?
**Transcript Section:**

Student: How do we write the equilibrium constant expression?

Assistant: Explained Kc for a reversible reaction.

**Expected output**

**Key Terms:**
- equilibrium constant
- Kc expression
- reversible reaction
- law of mass action

**Focused Query:** equilibrium constant Kc expression reversible reaction law of mass action

**Max Chunks:** 4

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Formula reference resolved to Kc expression only.

**Evaluators:** json_schema, max_chunks_range, coreference_resolution, scope_precision_check

---

#### Example 23: `scope_narrower-023`

- **Variation:** conversational_follow_up
- **Tags:** cbse, mathematics, source_pdf_kemh105

**Inputs**

**Query:** Why does that happen?
**Transcript Section:**

Student: Why does multiplying an inequality by a negative number reverse the inequality sign?

Assistant: Explained sign reversal rule for linear inequalities.

**Expected output**

**Key Terms:**
- linear inequalities
- sign reversal
- negative multiplication
- inequality properties

**Focused Query:** multiplying inequality by negative number reverses inequality sign rule

**Max Chunks:** 4

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Ambiguous follow-up resolved to sign-reversal concept.

**Evaluators:** json_schema, max_chunks_range, coreference_resolution, scope_precision_check

---

#### Example 24: `scope_narrower-024`

- **Variation:** conversational_follow_up
- **Tags:** cbse, chemistry, source_pdf_kech203

**Inputs**

**Query:** Explain the second point again.
**Transcript Section:**

Assistant: The factors affecting reaction rate are concentration, temperature, catalysts, and surface area.

**Expected output**

**Key Terms:**
- reaction rate
- temperature effect
- collision theory
- activation energy

**Focused Query:** effect of temperature on reaction rate collision theory activation energy

**Max Chunks:** 5

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Ordinal reference resolved to temperature-rate relationship only.

**Evaluators:** json_schema, max_chunks_range, coreference_resolution, scope_precision_check

---

#### Example 25: `scope_narrower-025`

- **Variation:** conversational_follow_up
- **Tags:** cbse, physics, source_pdf_leph201

**Inputs**

**Query:** What was the condition you mentioned earlier?
**Transcript Section:**

Student: When does total internal reflection occur?

Assistant: Explained the critical angle requirement.

**Expected output**

**Key Terms:**
- total internal reflection
- critical angle
- refractive index
- Snell law

**Focused Query:** critical angle condition total internal reflection refractive index requirement

**Max Chunks:** 4

**Quality Check:** Scope precision: pass. Intent preservation: pass. Retrieval readiness: pass. Non-overreach: pass. Follow-up resolved to critical-angle condition without over-expansion.

**Evaluators:** json_schema, max_chunks_range, coreference_resolution, scope_precision_check

---
